"""An expired token must not quietly become an anonymous socket.

The market socket authenticates ONCE, at the handshake, and the user's
spread cascade is read from that one decode. Returning None for a token
that failed to decode therefore didn't just lose the identity — it changed
the PRICES the socket streamed, from the user's own bid/ask to the global
admin one, while the REST quote poll kept serving the authenticated
numbers. A tab left open for days reconnects often enough (zombie
watchdog, wake from suspend, network blips) that the two kept swapping
places, which is the "price flicker" report.

    pytest -q backend/tests/test_market_ws_auth.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.api.ws.market_ws import WS_AUTH_FAILED, _resolve_user_id
from app.core.security import _encode, create_access_token, create_refresh_token

USER_ID = "507f1f77bcf86cd799439011"


def _access_token(*, age: timedelta = timedelta()) -> str:
    """An access token shifted in time, so "expired" can be tested without
    waiting out the real TTL."""
    now = datetime.now(timezone.utc) - age
    return _encode(
        {
            "sub": USER_ID,
            "role": "CLIENT",
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        }
    )


@pytest.mark.asyncio
async def test_no_token_is_still_anonymous():
    """A client that never sends one is a legitimate anonymous viewer."""
    assert await _resolve_user_id(None) is None
    assert await _resolve_user_id("") is None


@pytest.mark.asyncio
async def test_a_valid_token_resolves_the_user():
    token = create_access_token(user_id=USER_ID, role="CLIENT")
    assert await _resolve_user_id(token) == USER_ID


@pytest.mark.asyncio
async def test_an_expired_token_is_refused_not_downgraded():
    """The case that caused the flicker: the token decoded yesterday, the
    tab reconnected today, and the socket came back priced for nobody."""
    assert await _resolve_user_id(_access_token()) == USER_ID  # control
    stale = _access_token(age=timedelta(hours=1))
    with pytest.raises(PermissionError):
        await _resolve_user_id(stale)


@pytest.mark.asyncio
async def test_garbage_is_refused_too():
    with pytest.raises(PermissionError):
        await _resolve_user_id("not-a-jwt")


@pytest.mark.asyncio
async def test_a_refresh_token_cannot_authenticate_the_feed():
    """Only an ACCESS token. A refresh token reaching the query string
    would otherwise open a socket that outlives the access window."""
    token, _jti = create_refresh_token(user_id=USER_ID, role="CLIENT")
    with pytest.raises(PermissionError):
        await _resolve_user_id(token)


def test_the_close_code_is_the_one_the_client_listens_for():
    """Mirrors WS_AUTH_FAILED in frontend-user/lib/useMarketStream.ts — the
    client only refreshes its token when it sees exactly this code."""
    assert WS_AUTH_FAILED == 4401
