"""Who is online right now.

A user is "online" while their app holds the `/ws/user/{id}` socket
open. There is no logout event we can trust — tabs get closed, phones
sleep, networks drop — so presence is a Redis key with a TTL that the
socket's own 25 s heartbeat keeps alive. Stop heartbeating and the key
ages out on its own.

Deliberately NOT deleted on disconnect: a user with two tabs open would
otherwise vanish from the list the moment they closed one. Letting the
TTL decide means "online" always answers the same question — has this
user's app checked in recently — no matter how many sockets they have.

The stored value is when they came online, so the admin list can show
"online since" rather than just a dot.
"""

from __future__ import annotations

import logging
import time

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

_PREFIX = "presence:user:"
# Three missed heartbeats (25 s each) before a user drops off the list.
# Short enough to be believable, long enough that a tunnel or a lock
# screen doesn't flicker them in and out.
TTL_SEC = 90


def _key(user_id: str) -> str:
    return f"{_PREFIX}{user_id}"


async def mark_online(user_id: str) -> bool:
    """Called on connect and on every heartbeat.

    `SET NX` keeps the ORIGINAL online-since through reconnects and
    extra tabs; the separate EXPIRE refreshes the clock either way.

    Returns True only when this call is the one that brought the user
    ONLINE — the `SET NX` won. That makes it the offline→online
    transition, which is a different and much rarer event than "a
    heartbeat arrived": a user with three tabs open trips it once, and a
    reconnect inside the TTL does not trip it at all. Callers that want
    to act on someone coming online (rather than on every 25-second
    beat) key off this. False on a Redis failure, which fails quiet
    rather than firing a spurious transition.
    """
    try:
        r = get_redis()
        key = _key(str(user_id))
        first = bool(await r.set(key, str(int(time.time())), ex=TTL_SEC, nx=True))
        await r.expire(key, TTL_SEC)
        return first
    except Exception:  # pragma: no cover - presence is never load-bearing
        logger.debug("presence_mark_failed user=%s", user_id, exc_info=True)
        return False


async def online_user_ids() -> dict[str, int]:
    """`{user_id: online_since_epoch}` for everyone currently connected."""
    out: dict[str, int] = {}
    try:
        r = get_redis()
        # ponytail: SCAN + per-key GET. Fine into the low thousands of
        # concurrent users; swap for a sorted set keyed by last-seen if
        # this ever shows up in a profile.
        keys: list[str] = []
        async for key in r.scan_iter(match=f"{_PREFIX}*", count=500):
            keys.append(key if isinstance(key, str) else key.decode())
        if not keys:
            return out
        values = await r.mget(keys)
        for key, value in zip(keys, values, strict=False):
            uid = key[len(_PREFIX) :]
            try:
                out[uid] = int(value)
            except (TypeError, ValueError):
                # Key expired between SCAN and MGET, or holds junk —
                # treat as online now rather than dropping the row.
                out[uid] = int(time.time())
    except Exception:  # pragma: no cover
        logger.debug("presence_scan_failed", exc_info=True)
    return out
