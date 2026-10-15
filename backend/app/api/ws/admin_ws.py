"""Admin WebSocket channel — pushes platform-wide events live.

Auth: query params `?token=<admin_jwt>&key=<admin_api_key>` because
browsers can't add custom headers on a WebSocket handshake (so we mirror
the X-Admin-Api-Key check from `get_current_admin` via the query string).

Once authenticated the socket subscribes to a single global pub/sub
channel:

    admin:events   — every admin-relevant event across the platform
                     (position close, order fill, deposit submit/approve,
                     withdrawal submit/approve, KYC submit, etc.)

A message published on that channel is forwarded as-is to the browser,
which then invalidates the right React Query cache and re-renders the
affected admin page without anyone hitting F5.

One shared channel keeps the publish path cheap — emitters fire one
message no matter how many admins are watching — but it is NOT one
audience. ``publish_admin_event`` stamps each payload with
``recipient_admin_ids`` and the hub routes on it, so this socket only
receives events for users this viewer actually owns. It used to receive
every tenant's, including client names, user codes and deposit amounts,
with the filtering left to the browser.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.ws._helpers import safe_send_text
from app.core.config import settings
from app.core.security import decode_token
from app.core.ws_hub import admin_event_hub
from app.core.ws_limiter import acquire as ws_limit_acquire
from app.core.ws_limiter import client_ip as ws_client_ip
from app.core.ws_limiter import release as ws_limit_release
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter()


# Roles that are allowed to attach to the admin WS. Narrower than the
# `ADMIN_ROLES` set used by `get_current_admin`, which also admits
# EMPLOYEE — an employee's admin pages therefore get no realtime at all
# and fall back to polling. Pre-existing; left as-is because widening it
# is a product call, and `_scope_keys` would need `effective_scope_actor`
# to resolve an employee onto its parent admin's key.
_ADMIN_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.BROKER}


async def _scope_keys(user: User) -> list[str]:
    """Hub keys whose events this viewer is allowed to see.

    The values must match what `publish_admin_event` writes into
    `recipient_admin_ids`, i.e. what `push_service._compute_recipient_admin_ids`
    returns — attach under anything else and the socket sits on a key
    nothing is ever routed to, which looks like "the page stopped
    refreshing" rather than like an error.

      SUPER_ADMIN — its own id is only ever a recipient for
                    platform-direct users, so it takes the hub's
                    platform key and receives every scoped event too.
      BROKER      — its own id, which appears in every descendant's
                    `broker_ancestry`, so one key covers the whole
                    subtree (sub-brokers and their clients).
      ADMIN       — its own id PLUS the ids of the brokers in its pool.
                    The second half is not redundant. `reassign_user` does
                    re-stamp a transferred subtree's `assigned_admin_id`,
                    but in a bare `try` with no transaction and only for
                    rows that existed when that propagation was added — so
                    a partially-failed or pre-dating subtree sits on the
                    old owner's id. The REST scope reaches those rows
                    through the broker arm; without the same arm here this
                    socket would go quiet for a subtree the Users page
                    still lists, and a quiet socket reads as "the page
                    just stopped refreshing".
    """
    if user.role == UserRole.SUPER_ADMIN:
        return [admin_event_hub.SUPER_KEY]
    if user.role == UserRole.BROKER:
        return [str(user.id)]
    # Same query as `dependencies._admin_pool_clause` — that function
    # returns a Mongo clause, and we need the ids themselves.
    # ponytail: resolved once at connect, so a broker created or
    # transferred mid-session reaches this admin only after the browser
    # reconnects. Re-resolve on a `broker` admin event if that bites.
    keys = [str(user.id)]
    try:
        coll = User.get_motor_collection()
        async for doc in coll.find({"role": UserRole.BROKER.value, "assigned_admin_id": user.id}, {"_id": 1}):
            keys.append(str(doc["_id"]))
    except Exception as e:  # pragma: no cover
        # Degrade to the admin's own id rather than refusing the socket:
        # a thinner feed is recoverable by F5, a dropped connection isn't,
        # and widening on error would hand over another tenant's events.
        logger.warning("admin_ws_broker_keys_failed", extra={"error": str(e)})
    return keys


@router.websocket("/ws/admin")
async def admin_ws(
    ws: WebSocket,
    token: str = Query(...),
    key: str = Query(..., description="Admin API key — same value as the X-Admin-Api-Key header"),
):
    """Admin event WebSocket.

    Internal change: connects to the process-wide ``AdminEventHub``
    instead of opening a dedicated Redis pub/sub connection. The hub
    subscribes to ``admin:events`` once per worker and fans every
    message out to every attached admin socket. Auth, message format
    and heartbeat behaviour are unchanged.
    """
    # ── Auth ────────────────────────────────────────────────────────
    # 1) API-key gate (same value the HTTP dependency checks). Without
    #    this the admin role check below would be the only barrier — and
    #    the HTTP layer enforces both, so the WS should match.
    expected = settings.ADMIN_API_KEY.get_secret_value()
    if not expected or key != expected:
        await ws.close(code=4401)
        return

    # 2) JWT — admin access token, same shape as the HTTP bearer.
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
    except Exception:
        await ws.close(code=4401)
        return
    if not user_id:
        await ws.close(code=4401)
        return

    # 3) Admin role gate (DB lookup so a freshly-demoted account can't
    #    keep a stale socket open). Beanie is initialised by the lifespan
    #    so a direct `.get` is safe here.
    try:
        from beanie import PydanticObjectId

        user = await User.get(PydanticObjectId(user_id))
    except Exception:
        await ws.close(code=4401)
        return
    if user is None or user.role not in _ADMIN_ROLES:
        await ws.close(code=4403)
        return

    # Per-IP rate limit — reject before accept() so a flooding client
    # doesn't get a slot. Code 4429 mirrors HTTP 429.
    ip = ws_client_ip(ws)
    if not await ws_limit_acquire(ip, max_per_ip=settings.WS_MAX_CONNECTIONS_PER_IP):
        await ws.close(code=4429)
        return

    await ws.accept()
    await safe_send_text(
        ws,
        json.dumps({"type": "hello", "user_id": str(user.id), "role": user.role.value}),
    )

    # Hub is started eagerly in the FastAPI lifespan; ``start()`` is
    # idempotent so a stray race here is still safe.
    try:
        await admin_event_hub.start()
    except Exception as e:  # pragma: no cover
        logger.warning("admin_ws_hub_start_failed", extra={"error": str(e)})
        await ws.close(code=4500)
        return

    admin_event_hub.attach(ws, await _scope_keys(user))

    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(25)
                if not await safe_send_text(ws, json.dumps({"type": "heartbeat"})):
                    return
        except (WebSocketDisconnect, asyncio.CancelledError):
            return
        except Exception:  # pragma: no cover
            return

    hb_task = asyncio.create_task(heartbeat())

    try:
        # The hub forwards admin events to this socket. We only need
        # to keep the connection alive and drain anything the client
        # sends (so receive_text raises WebSocketDisconnect on close).
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        return
    except Exception as e:  # pragma: no cover
        logger.warning("admin_ws_failed", extra={"error": str(e)})
    finally:
        hb_task.cancel()
        try:
            await hb_task
        except (asyncio.CancelledError, Exception):  # pragma: no cover
            pass
        try:
            admin_event_hub.detach(ws)
        except Exception:  # pragma: no cover
            pass
        try:
            await ws_limit_release(ip)
        except Exception:  # pragma: no cover
            pass
