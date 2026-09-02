"""Single publish helper for the `admin:events` pub/sub channel.

Why a dedicated module: the admin WebSocket subscribes to ONE channel
(`admin:events`) rather than per-admin queues, so every emitter funnels
through a single function. That keeps the publish path one line at every
call site:

    await publish_admin_event("position_closed", {"user_id": ..., "id": ...})

The frontend's `AdminWsBridge` switches on the `type` field and
invalidates the matching React Query keys (positions / orders / wallet /
deposits / withdrawals / kyc). Adding a new event type just means
publishing it here and adding a case to the bridge.

Failures are logged + swallowed — a missing Redis must never block the
HTTP / WS request that triggered the event, exactly like the user-side
publishers in `wallet_service` and `admin/trading.py`.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.redis_client import publish

logger = logging.getLogger(__name__)

ADMIN_CHANNEL = "admin:events"


async def publish_admin_event(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Publish a JSON event to the global `admin:events` channel.

    Args:
        event_type: One of the strings the AdminWsBridge knows about
                    (`position_update`, `order_update`, `deposit_update`,
                    `withdrawal_update`, `kyc_update`, `wallet_update`).
        payload: Anything JSON-serialisable. The frontend doesn't rely on
                 the body for invalidation (the `type` alone tells it
                 which query keys to refresh) — payload is just for
                 future fine-grained handling.
    """
    body = {"type": event_type, **(payload or {})}
    try:
        await publish(ADMIN_CHANNEL, body)
    except Exception:  # pragma: no cover
        # Swallow — never let a pub/sub hiccup take down the calling
        # request. The admin dashboard's polling still keeps numbers
        # eventually-consistent if a single publish is lost.
        logger.exception("admin_event_publish_failed", extra={"type": event_type})
