"""Single publish helper for the `admin:events` pub/sub channel.

Why a dedicated module: the admin WebSocket subscribes to ONE Redis
channel (`admin:events`) rather than per-admin queues, so every emitter
funnels through a single function. That keeps the publish path one line
at every call site:

    await publish_admin_event("position_closed", {"user_id": ..., "id": ...})

The frontend's `AdminWsBridge` switches on the `type` field and
invalidates the matching React Query keys (positions / orders / wallet /
deposits / withdrawals / kyc). Adding a new event type just means
publishing it here and adding a case to the bridge.

ONE channel does NOT mean one audience. This function stamps every event
with `recipient_admin_ids` — the operators who own the event's subject —
and `AdminEventHub._route_keys` delivers only to those sockets. That is
load-bearing, not cosmetic: these payloads carry client names, user codes
and deposit amounts, and before this every attached admin/broker socket
received every tenant's events, so a sub-broker with DevTools open could
read the whole platform's traffic live. Resolving the audience HERE
rather than at the two dozen call sites is the only reason the fix is
small — an emitter that forgets to scope its payload gets scoped anyway.

Failures are logged + swallowed — a missing Redis must never block the
HTTP / WS request that triggered the event, exactly like the user-side
publishers in `wallet_service` and `admin/trading.py`.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.redis_client import publish

# Top-level, unlike the other service imports in this module: the routing
# below runs on EVERY admin event, so a per-call deferred import would be
# pure overhead. Safe because push_service pulls in no services itself.
from app.services.push_service import _compute_recipient_admin_ids

logger = logging.getLogger(__name__)

ADMIN_CHANNEL = "admin:events"

# Payload fields that name the SUBJECT of an event, in priority order.
# `_compute_recipient_admin_ids` answers "who is ABOVE this row", so the
# subject itself is always added back on top of that — do NOT special-case
# `user_id` as "must be a trader". `wallet_service._publish_wallet_event`
# publishes `{"user_id": <operator id>}` for a P&L-sharing payout or
# receipt (`pnl_sharing_service` debits the broker and credits the admin
# by id), and without the subject in its own audience the operator whose
# money just moved is the one party whose wallet tile never refreshes.
# Adding it costs nothing when the subject IS a trader: admin sockets key
# on operator ids only, so a client id in the list matches no subscriber.
#
# A payload with none of these has no tenant to scope to; see
# `_resolve_recipients`.
_SUBJECT_FIELDS = ("user_id", "broker_id", "admin_id")


async def _resolve_recipients(body: dict[str, Any]) -> list[str] | None:
    """Operator ids that may see this event, or None if it has no subject.

    `push_service._compute_recipient_admin_ids` is the canonical "which
    admins own this user" resolver (assigned_admin_id + every broker in
    `broker_ancestry`, falling back to the super-admins for a
    platform-direct user) — the same answer the notification bell and the
    web-push fan-out already use, so the socket now agrees with them
    instead of inventing a third scope rule.

    ponytail: one primary-key User read per event — a market order fires
    three. Memoise per user_id with a short TTL if it ever shows up in a
    profile, but remember a transfer has to invalidate it.
    """
    for field in _SUBJECT_FIELDS:
        subject = body.get(field)
        if not subject:
            continue
        ids = {str(o) for o in await _compute_recipient_admin_ids(subject)}
        ids.add(str(subject))
        return sorted(ids)
    return None


async def publish_admin_event(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Publish a JSON event to the global `admin:events` channel.

    Args:
        event_type: One of the strings the AdminWsBridge knows about
                    (`position_update`, `order_update`, `deposit_update`,
                    `withdrawal_update`, `kyc_update`, `wallet_update`).
        payload: Anything JSON-serialisable. The frontend doesn't rely on
                 the body for invalidation (the `type` alone tells it
                 which query keys to refresh) — payload is just for
                 future fine-grained handling. A `recipient_admin_ids`
                 key already in the payload is trusted as-is; otherwise
                 it is derived from the subject (`_SUBJECT_FIELDS`) and
                 the hub routes on it.
    """
    body = {"type": event_type, **(payload or {})}
    # `not .get(...)`, not `not in`: `user/wallet.py` pre-seeds
    # `recipient_ids = []` before a try/except around its owner lookup, so a
    # DB blip there publishes an EMPTY audience. Trusting that would route the
    # deposit to super-admins only and leave the owning admin's inbox stale —
    # re-resolving from `user_id` gives the identical set when the lookup
    # works and falls back to broadcast when it doesn't.
    if not body.get("recipient_admin_ids"):
        try:
            recipients = await _resolve_recipients(body)
        except Exception:
            # A resolver hiccup must not silence the dashboard. An event
            # that stops arriving reads as "the page just doesn't refresh
            # any more" — much harder to notice than one extra refetch —
            # so we fall through to broadcast by leaving the key off.
            logger.exception("admin_event_scope_failed", extra={"type": event_type})
            recipients = None
        if recipients is None:
            # No subject, so platform-level: broadcast, as before this
            # change. Logged loudly because every event type that exists
            # today carries one of `_SUBJECT_FIELDS` — this line firing
            # means a new emitter needs classifying.
            logger.warning("admin_event_unscoped", extra={"type": event_type})
        else:
            body["recipient_admin_ids"] = recipients
    try:
        await publish(ADMIN_CHANNEL, body)
    except Exception:  # pragma: no cover
        # Swallow — never let a pub/sub hiccup take down the calling
        # request. The admin dashboard's polling still keeps numbers
        # eventually-consistent if a single publish is lost.
        logger.exception("admin_event_publish_failed", extra={"type": event_type})


async def trade_alert_fields(
    user_id: Any,
    *,
    action: str,
    quantity: float,
    price: Any,
    symbol: str,
    event: str,
) -> dict[str, Any]:
    """Extra publish fields for a fill on a user the admin is watching.

    Returns ``{}`` — the normal case — when the user's `trade_alert` flag
    is off, so the fill path costs exactly one projected read. When it IS
    on, the payload carries everything the toast needs plus the
    `recipient_admin_ids` scope filter the deposit / withdrawal toasts
    already use, so one admin's watch never rings in another's panel.
    """
    from beanie import PydanticObjectId

    from app.models.user import User

    try:
        doc = await User.get_motor_collection().find_one(
            {"_id": PydanticObjectId(str(user_id))},
            {
                "trade_alert": 1,
                "trade_alert_sound": 1,
                "full_name": 1,
                "user_code": 1,
            },
        )
        if not doc or not doc.get("trade_alert"):
            return {}
        from app.services.push_service import _compute_recipient_admin_ids

        recipients = await _compute_recipient_admin_ids(str(user_id))
        return {
            "recipient_admin_ids": [str(r) for r in recipients],
            "alert": {
                "sound": doc.get("trade_alert_sound") or "chime",
                "user_name": doc.get("full_name") or "",
                "user_code": doc.get("user_code") or "",
                "action": action,
                "qty": quantity,
                "price": float(price),
                "symbol": symbol,
                "event": event,
            },
        }
    except Exception:
        # Never let the alert lookup break a fill — the publish still goes
        # out without it and the admin's tables refresh as before.
        logger.exception("trade_alert_fields_failed")
        return {}
