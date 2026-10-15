"""Admin notification fan-out — one source event → one row per admin
recipient up the user's tier chain.

The admin notification bell on the top-right of every admin /
super-admin / broker / sub-broker dashboard reads from
`admin_notifications` (model defined in `app/models/notification.py`).
Each row is per-(recipient_admin, event) so the bell query is a flat
`find({recipient_admin_id: me})` — no reverse-walking through the
user hierarchy at read time.

Public surface:

  create_for_admins(
    source_user_id,
    event_type, title, message,
    *, level=INFO, link=None,
    reference_type=None, reference_id=None, data=None,
  )
      Resolves the recipient set for a source user (every
      super-admin + the user's assigned admin + every broker in
      their ancestry) and inserts one AdminNotification row per
      recipient. Publishes a single `notification_created` admin
      event over Redis pub/sub so all attached admin browsers
      invalidate their bell query and refetch — the WS payload
      carries the recipient_admin_ids so each frontend can decide
      whether the refetch is theirs to act on.

      Best-effort: a Mongo / Redis hiccup on the notification
      side MUST NOT roll back the caller's primary write. Every
      branch in this module either swallows or logs+swallows
      exceptions.
"""

from __future__ import annotations

import logging
from typing import Any

from beanie import PydanticObjectId

from app.core.dependencies import _pool_clause, merge_scope
from app.core.redis_client import publish_batch
from app.models.notification import (
    AdminNotification,
    AdminNotificationEventType,
    Notification,
    NotificationLevel,
    NotificationType,
)
from app.models.user import User, UserRole, UserStatus

logger = logging.getLogger(__name__)


async def _resolve_recipients(
    source_user: User,
) -> list[PydanticObjectId]:
    """Walk the source user's tier chain and return the list of admin
    ids that should receive a notification when an event fires on this
    user.

    Recipients (deduplicated, order doesn't matter — each row is its
    own document):

      1. The user's OWNER admin ONLY — `source_user.assigned_admin_id`
         when set, otherwise every SUPER_ADMIN (the platform pool). So a
         super-admin sees ONLY their own pool's users, and one sub-admin
         never sees another sub-admin's users.
      2. Every broker id in `source_user.broker_ancestry` — root-first
         list up to the immediate parent (each broker / sub-broker sees
         its own subtree).
      3. `source_user.assigned_broker_id` if set and not already in
         the ancestry list — covers legacy rows whose ancestry hasn't
         been backfilled yet.

    Admin-role users (SUPER_ADMIN / ADMIN / BROKER) themselves never
    produce notifications about their own actions — the function
    accepts any User but the caller is expected to pass an end-user
    (CLIENT / DEALER / MASTER). Defensive: if the source is admin-
    tier we still resolve their chain anyway (e.g. an admin
    submitting a deposit on behalf of themselves — rare but possible).
    """
    recipients: set[PydanticObjectId] = set()

    # Tier ownership — each tier sees ONLY the users in its own pool:
    #   • user HAS an assigned sub-admin  → that admin owns it; super-admins
    #     do NOT get it (so one admin never sees another admin's users).
    #   • user has NO sub-admin (platform pool) → every super-admin owns it.
    # Operator-flagged: "ek admin ko 2 admin ka mat dikhao; super-admin ko
    # bhi sirf uske apne users ka dikhe."
    if source_user.assigned_admin_id is not None:
        recipients.add(source_user.assigned_admin_id)
    else:
        try:
            supers = await User.find(User.role == UserRole.SUPER_ADMIN).to_list()
            for s in supers:
                if s.id is not None:
                    recipients.add(s.id)
        except Exception:  # pragma: no cover
            logger.exception("notif_resolve_super_admins_failed")

    # Brokers / sub-brokers in the user's chain get their subtree's events.
    for broker_id in source_user.broker_ancestry or []:
        recipients.add(broker_id)

    if (
        source_user.assigned_broker_id is not None
        and source_user.assigned_broker_id not in recipients
    ):
        recipients.add(source_user.assigned_broker_id)

    # An end-user shouldn't be their own admin notification recipient —
    # they have the user-side `Notification` model for self-facing
    # alerts. Strip the source id if it accidentally landed in the set.
    if source_user.id is not None:
        recipients.discard(source_user.id)

    return list(recipients)


async def create_for_admins(
    source_user_id: str | PydanticObjectId,
    event_type: AdminNotificationEventType,
    title: str,
    message: str,
    *,
    level: NotificationLevel = NotificationLevel.INFO,
    link: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> int:
    """Fan an event out into AdminNotification rows for every admin in
    the source user's tier chain. Returns the number of rows inserted.

    All branches swallow exceptions so a notification failure never
    rolls back the calling endpoint's primary write (deposit save,
    KYC submit, etc.).
    """
    try:
        uid = PydanticObjectId(str(source_user_id))
    except Exception:
        logger.warning("notif_invalid_source_user_id %s", source_user_id)
        return 0

    try:
        source = await User.get(uid)
    except Exception:  # pragma: no cover
        logger.exception("notif_source_user_lookup_failed user=%s", uid)
        return 0
    if source is None:
        logger.warning("notif_source_user_not_found user=%s", uid)
        return 0

    recipients = await _resolve_recipients(source)
    if not recipients:
        return 0

    # Enrich `data` with a few common fields the frontend rendering
    # leans on (user_name, user_code) so the bell row can show the
    # full identity without a separate lookup per render.
    enriched: dict[str, Any] = dict(data or {})
    enriched.setdefault("user_name", source.full_name)
    enriched.setdefault("user_code", source.user_code)

    rows: list[AdminNotification] = []
    for recipient_id in recipients:
        rows.append(
            AdminNotification(
                recipient_admin_id=recipient_id,
                source_user_id=uid,
                event_type=event_type,
                level=level,
                title=title,
                message=message,
                link=link,
                reference_type=reference_type,
                reference_id=reference_id,
                data=enriched,
            )
        )

    try:
        await AdminNotification.insert_many(rows)
    except Exception:  # pragma: no cover
        logger.exception(
            "notif_insert_many_failed user=%s event=%s count=%d",
            uid,
            event_type.value,
            len(rows),
        )
        return 0

    # Fan-out so every attached admin WS refreshes its bell. Payload
    # carries the recipient list so the frontend can decide quickly
    # whether it should refetch (the WS channel is shared across all
    # admins, but each browser only cares about events touching them).
    try:
        from app.services.admin_events import publish_admin_event

        await publish_admin_event(
            "notification_created",
            {
                "event_type": event_type.value,
                "source_user_id": str(uid),
                "recipient_admin_ids": [str(r) for r in recipients],
                "title": title,
                "level": level.value,
            },
        )
    except Exception:  # pragma: no cover
        logger.exception("notif_publish_event_failed")

    return len(rows)


# ── Payment details changed ──────────────────────────────────────────
async def notify_payment_details_changed(actor, what: str) -> int:
    """Tell everyone who could be shown the actor's deposit details that
    they changed.

    Scoped to the actor's POOL, because that is the set the resolver can
    reach. `user/wallet.py::company_banks` (and `crypto_config_service.
    resolve_for_user`) picks the FIRST owner with rows while walking
    immediate broker → every parent broker in `broker_ancestry`, tip to
    root → assigned admin → platform default. So "whose bank does this
    user see" is an UPWARD walk, and the notice has to be the mirror of
    it: every user BELOW the actor is a candidate.

    The old version used `assigned_broker_id == actor.id` for BROKER and
    argued the subtree was deliberately excluded — "a broker's client
    deposits into the broker's account". That holds only for a broker's
    DIRECT clients. A sub-broker who never authored a bank row inherits
    this broker's, so its clients deposit into THIS account and were
    never told it changed. Same hole one tier up: a broker chain with no
    rows anywhere falls through to the admin, so the ADMIN arm needs the
    transferred-broker subtree too — which is exactly `_pool_clause`.

    The narrow behaviour was right about one thing: alerts that don't
    apply train people to ignore them. The trade is not symmetric here,
    though. Over-notifying costs a shrug; under-notifying means someone
    wires money to a closed account, so the superset wins.

    EMPLOYEE is the one role where `_pool_clause` is NOT a superset, so it
    gets BOTH arms. `_pool_clause` resolves an employee to its parent admin,
    which is right for the parent's clients — but `POST /admin/users` picks
    the ownership chain with `if SUPER_ADMIN / elif BROKER / else: # ADMIN`,
    and an employee actor lands in that else, stamping
    `assigned_admin_id = <employee>.id` (users.py:941). Those orphan clients
    really do read the employee's own rows: `crypto_config_service` has no
    EMPLOYEE arm either, so an employee's crypto-config write is stored
    under `owner_admin_id = <employee>.id` and `resolve_for_user` matches it
    by that exact id. Resolving to the parent alone would have left them
    looking at a stale deposit address with nobody told — the precise
    failure this function exists to prevent, for the one role that cannot
    see it coming.

    Returns how many users were notified. Best-effort throughout: a
    failure here must never fail the bank edit that triggered it.
    """
    # ponytail: pool-wide superset, not the exact resolver result. Pinning
    # it would mean replaying the per-user cascade (one query per user per
    # tier) to find whose first-owner-with-rows is actually the actor. If
    # the noise ever becomes the complaint, the cheap 90% is to drop any
    # sub-broker subtree that owns its own CompanyBankAccount rows.
    #
    # merge_scope, not query.update: the ADMIN clause is an `$or` and so is
    # nothing else here today — but a dropped scope clause raises nothing,
    # it just widens the blast radius of a money alert.
    pool = await _pool_clause(actor)
    if actor.role == UserRole.EMPLOYEE:
        # Union, not replace: the parent's clients AND the employee's own
        # orphans. See the EMPLOYEE paragraph above — dropping either half
        # means someone sends money to an address nobody told them changed.
        pool = {"$or": [pool, {"assigned_admin_id": actor.id}]}
    query: dict = merge_scope(
        {"role": UserRole.CLIENT.value, "status": UserStatus.ACTIVE.value},
        pool,
    )

    recipients = [u.id for u in await User.find(query).to_list()]
    if not recipients:
        return 0

    title = "Deposit details updated"
    message = (
        f"{what} has changed. Please use the latest details shown on the "
        "deposit screen before sending any money."
    )
    # The SAME warning, said two ways on purpose.
    #
    # `message` is the real one and it goes to the bell and the socket,
    # neither of which anybody filters. The Web Push copy cannot be that
    # sentence: Chrome runs an on-device spam classifier over every
    # Android notification's title and body, and "the account details
    # changed, use the new ones before you send money" is, word for word,
    # the shape of a payment-redirection scam. The classifier cannot tell
    # our warning from the fraud it warns about — and it is not wrong to
    # be suspicious of that sentence.
    #
    # A flagged notification is replaced by "Possible spam" with an
    # Unsubscribe button that REVOKES the site's notification permission
    # outright, so one bad-looking push costs that user every future one.
    # So the push says only enough to get them into the app, where the
    # full wording above is waiting. No amount, no instruction to pay, no
    # urgency word.
    push_body = "Your deposit page has been updated — open the app to see the current details."

    await Notification.insert_many(
        [
            Notification(
                user_id=uid,
                type=NotificationType.SYSTEM,
                level=NotificationLevel.WARNING,
                title=title,
                message=message,
                data={"link": "/wallet", "category": "payment"},
            )
            for uid in recipients
        ]
    )

    payload = {
        "type": "notification",
        "payload": {
            "title": title,
            "message": message,
            "link": "/wallet",
            "level": "WARNING",
            # Picks the tone on the client. Money details changing is not
            # the same event as money arriving, and it should not sound
            # like it.
            "category": "payment",
        },
    }
    try:
        await publish_batch(
            [(f"user:{uid}:notification", payload) for uid in recipients]
        )
    except Exception:  # pragma: no cover - never fail the edit
        logger.exception("payment_details_notify_publish_failed actor=%s", actor.id)

    # Web Push as well as the socket. The socket only reaches a tab that
    # is open; this is the alert most likely to matter when the app is
    # CLOSED, because the next thing the user does is open their bank
    # app and send money to whatever account they remember. Best-effort
    # and no-ops when VAPID is unconfigured, same as the broadcast path.
    try:
        from app.services import push_service

        await push_service.send_to_users(
            recipients,
            title=title,
            body=push_body,
            url="/wallet",
            tag=f"mp-payment-{actor.id}",
        )
    except Exception:  # pragma: no cover
        logger.exception("payment_details_webpush_failed actor=%s", actor.id)

    logger.info(
        "payment_details_changed_notified actor=%s role=%s users=%d",
        actor.id,
        actor.role,
        len(recipients),
    )
    return len(recipients)
