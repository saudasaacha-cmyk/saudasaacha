"""Who is online, and why the rules are the way they are.

Presence is a Redis key with a TTL that the socket's own heartbeat
keeps alive. The two decisions worth pinning:

  • the key is NOT cleared on disconnect — a user with two tabs open
    would vanish the moment they closed one;
  • `online_since` survives reconnects, so the admin list shows when the
    session started rather than when the last packet arrived.

    pytest -q backend/tests/test_presence.py
"""

from __future__ import annotations

import inspect

from app.services import presence_service


def test_the_window_covers_more_than_one_missed_heartbeat():
    """The socket beats every 25 s. A TTL at or under that would drop
    anyone whose phone paused for a second."""
    from app.api.ws.user_ws import _heartbeat

    beat = inspect.getsource(_heartbeat)
    assert "asyncio.sleep(25)" in beat
    assert presence_service.TTL_SEC >= 25 * 3


def test_disconnect_does_not_clear_presence():
    """Two tabs, close one, still online. There is no delete anywhere in
    the service for exactly that reason."""
    src = inspect.getsource(presence_service)
    assert "def mark_offline" not in src
    assert ".delete(" not in src


def test_online_since_survives_a_reconnect():
    """SET NX keeps the original timestamp; the EXPIRE is what refreshes
    the clock. Writing the value unconditionally would restart the
    'online for' counter on every heartbeat."""
    src = inspect.getsource(presence_service.mark_online)
    assert "nx=True" in src
    assert "expire(" in src


def test_the_heartbeat_is_what_refreshes_it():
    """If beats stop, so does the refresh — that is the whole mechanism."""
    from app.api.ws.user_ws import _heartbeat

    beat = inspect.getsource(_heartbeat)
    assert beat.count("mark_online") == 2  # once on connect, once per beat


def test_the_admin_list_is_scoped_like_every_other_user_list():
    """An admin must not see the platform's users in this card."""
    from app.api.v1.admin.users import list_online_users

    src = inspect.getsource(list_online_users)
    assert "scoped_user_filter(admin)" in src


def test_a_junk_presence_key_cannot_break_the_page():
    """Keys are scanned from Redis, so a stray one must be skipped
    rather than raising out of the endpoint."""
    from app.api.v1.admin.users import list_online_users

    src = inspect.getsource(list_online_users)
    assert "continue" in src
