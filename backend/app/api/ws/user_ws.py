"""User WebSocket channel — pushes order/position/wallet events live.

Auth: query param `?token=<jwt>` (browsers can't add custom headers on WS).

Subscribes the authenticated user's socket to two Redis pub/sub channels:
    user:{user_id}:positions   — admin edits / force-close events
    user:{user_id}:orders      — order status changes (fills, rejects)
    user:{user_id}:wallet      — balance / margin changes

Any message published on those channels is forwarded as-is to the browser,
which then invalidates the right React Query cache and re-renders without
a page refresh.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.ws._helpers import safe_send_text
from app.core.config import settings
from app.core.security import decode_token
from app.core.ws_hub import user_channel_hub
from app.core.ws_limiter import acquire as ws_limit_acquire
from app.core.ws_limiter import client_ip as ws_client_ip
from app.core.ws_limiter import release as ws_limit_release
from app.services import presence_service, telecrm_service

logger = logging.getLogger(__name__)
router = APIRouter()


async def _heartbeat(ws: WebSocket, user_id: str) -> None:
    """Keep the socket warm and the user's presence fresh.

    The two belong together: presence is "this app checked in recently",
    and the heartbeat IS the check-in. Marked once on connect, refreshed
    on every beat, and left to expire on its own — see
    `presence_service` for why a disconnect doesn't clear it.
    """
    # The CRM wants "came online", not "is still online". `mark_online`
    # answers True only for the call that actually won the SET NX, so a
    # user with three tabs pushes once and the 25-second beat below never
    # pushes at all.
    if await presence_service.mark_online(user_id):
        telecrm_service.push_user_bg(user_id, online_since=int(time.time()))
    try:
        while True:
            await asyncio.sleep(25)
            if not await safe_send_text(ws, json.dumps({"type": "heartbeat"})):
                return
            await presence_service.mark_online(user_id)
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
    except Exception:  # pragma: no cover
        return


@router.websocket("/ws/user")
async def user_ws(ws: WebSocket, token: str = Query(...)):
    """Per-user event WebSocket.

    Internal change: events arrive via the process-wide
    ``UserChannelHub`` (one shared Redis pub/sub psubscribed to
    ``user:*`` for the whole worker) instead of opening a dedicated
    pub/sub connection for every connected user. The hub routes each
    inbound message by the ``{id}`` segment of its channel name, so
    every existing publisher (positions, orders, wallet, kyc, risk,
    pnl_sharing, deposit_update, withdrawal_update, etc.) keeps
    working with no code changes on the emitter side.

    The wire protocol the client speaks (hello frame, JSON
    pass-through, 25 s heartbeats) is unchanged.
    """
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            await ws.close(code=4401)
            return
    except Exception:
        await ws.close(code=4401)
        return

    # Per-IP rate limit — reject before accept() so a flooding client
    # doesn't get a slot. Code 4429 mirrors HTTP 429.
    ip = ws_client_ip(ws)
    if not await ws_limit_acquire(ip, max_per_ip=settings.WS_MAX_CONNECTIONS_PER_IP):
        await ws.close(code=4429)
        return

    await ws.accept()
    await safe_send_text(ws, json.dumps({"type": "hello", "user_id": user_id}))

    # Hub is started eagerly in the FastAPI lifespan. ``start()`` is
    # idempotent so a stray race here is still safe.
    try:
        await user_channel_hub.start()
    except Exception as e:  # pragma: no cover
        logger.warning("user_ws_hub_start_failed", extra={"error": str(e)})
        await ws.close(code=4500)
        return

    user_channel_hub.add(str(user_id), ws)

    hb_task = asyncio.create_task(_heartbeat(ws, str(user_id)))

    try:
        # The hub is now responsible for forwarding messages to this
        # socket. We only need to keep the connection alive and drain
        # anything the client sends (so receive_text raises
        # WebSocketDisconnect on close instead of buffering forever).
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        return
    except Exception as e:  # pragma: no cover
        logger.warning("user_ws_failed", extra={"error": str(e)})
    finally:
        hb_task.cancel()
        try:
            await hb_task
        except (asyncio.CancelledError, Exception):  # pragma: no cover
            pass
        try:
            user_channel_hub.remove(str(user_id), ws)
        except Exception:  # pragma: no cover
            pass
        try:
            await ws_limit_release(ip)
        except Exception:  # pragma: no cover
            pass
