"""Daily purge of the login IPs recorded against admin-tier accounts.

An admin's login IP lands in TWO places, and both are wiped together —
clearing one and leaving the other is the trap this service exists to
avoid:

* ``User.last_login_ip`` — one value per account, overwritten on every
  login by ``User.mark_login``. Nothing in the panel renders it, so an
  operator has no way to tell it is sitting there.
* ``AuditLog.ip_address`` on that account's LOGIN / LOGOUT /
  LOGIN_FAILED rows — this is the IP column on the Audit logs page.

Only SUPER_ADMIN / ADMIN / BROKER rows are touched (a sub-broker carries
BROKER, so it is included). A trading client's login IP is deliberately
left alone.

The audit ROWS themselves survive — only the `ip_address` field is
unset — so "who logged in, and when" is still answerable afterwards;
only "from where" goes. And the purge is itself audited
(``LOGIN_IP_PURGE``) with the counts, carrying no ip_address of its own:
clearing the trail still leaves a trail.

Fires once per IST day at ``PURGE_AT`` (00:00), and on demand from the
Platform Settings card. The last-run day lives in Redis, so a redeploy
at 02:00 does not re-fire the purge that already ran at midnight — which
would otherwise wipe the IPs of logins that happened *since* it.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from datetime import time as _dtime
from typing import Any

from beanie import PydanticObjectId

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User, UserRole
from app.services.audit_service import log_event
from app.utils.time_utils import UTC, now_ist, start_of_day_ist

logger = logging.getLogger(__name__)

# The admin tier, as the operator defined it: super admin, every
# sub-admin, every broker and sub-broker.
TIER_ROLES: list[str] = [
    UserRole.SUPER_ADMIN.value,
    UserRole.ADMIN.value,
    UserRole.BROKER.value,
]

# Only the login-shaped audit rows give up their IP. A WALLET_ADJUST or
# SETTING_CHANGE row keeps its IP so a money move is still traceable to
# a machine.
LOGIN_ACTIONS: list[str] = [
    AuditAction.LOGIN.value,
    AuditAction.LOGOUT.value,
    AuditAction.LOGIN_FAILED.value,
]

# Midnight IST. The loop fires on the first poll of a new IST day, which
# at 00:00 is the same thing — change this and the `>= PURGE_AT` guard
# below starts doing real work.
PURGE_AT: _dtime = _dtime(hour=0, minute=0)

_LAST_DAY_KEY = "admin_ip:last_purge_day"
# Longer than a day so a cluster that was down over midnight still finds
# the marker and skips, but short enough that a stale key can't park the
# purge forever.
_LAST_DAY_TTL = 3 * 24 * 3600

# How many of the stored IPs the settings card previews. The super admin
# is the one person allowed to read these, and seeing what is actually
# there is what makes the button's effect concrete.
_SAMPLE_LIMIT = 10

# The Motor client is tz_aware, so every datetime read off a row is
# offset-aware. A naive sentinel (datetime.min) would raise rather than
# sort the moment one admin row carries an IP but no last_login_at — a
# hand-edited row or a half-written login is enough.
_NEVER = datetime.min.replace(tzinfo=UTC)

_stop = False


def stop_admin_ip_cleanup() -> None:
    global _stop
    _stop = True


async def _tier_users() -> list[User]:
    return await User.find({"role": {"$in": TIER_ROLES}}).to_list()


async def _last_purge_at() -> datetime | None:
    """When the last purge ran, read back off its own audit row.

    No extra bookkeeping collection: the purge already writes an audit
    row, so that row IS the record.
    """
    row = (
        await AuditLog.find({"action": AuditAction.LOGIN_IP_PURGE.value})
        .sort("-created_at")
        .limit(1)
        .to_list()
    )
    return row[0].created_at if row else None


def _next_purge_at(now: datetime | None = None) -> datetime:
    """The next time the daily purge will fire, in IST."""
    now = now or now_ist()
    today = start_of_day_ist(now.date()).replace(
        hour=PURGE_AT.hour, minute=PURGE_AT.minute
    )
    return today if now < today else today + timedelta(days=1)


async def stats() -> dict[str, Any]:
    """What is currently stored, for the Platform Settings card."""
    users = await _tier_users()
    ids = [u.id for u in users]
    with_ip = [u for u in users if u.last_login_ip]
    audit_rows = (
        await AuditLog.find(
            {
                "user_id": {"$in": ids},
                "action": {"$in": LOGIN_ACTIONS},
                "ip_address": {"$ne": None},
            }
        ).count()
        if ids
        else 0
    )
    # Newest login first — the ones an operator cares about.
    with_ip.sort(key=lambda u: u.last_login_at or _NEVER, reverse=True)
    return {
        "accounts": len(users),
        "accounts_with_ip": len(with_ip),
        "audit_rows_with_ip": audit_rows,
        "samples": [
            {
                "user_code": u.user_code,
                "full_name": u.full_name,
                "role": str(u.role.value if hasattr(u.role, "value") else u.role),
                "ip": u.last_login_ip,
                "last_login_at": u.last_login_at,
            }
            for u in with_ip[:_SAMPLE_LIMIT]
        ],
        "last_purge_at": await _last_purge_at(),
        "purge_at_ist": PURGE_AT.strftime("%H:%M"),
        "next_purge_at": _next_purge_at(),
    }


async def purge(
    *, actor_id: PydanticObjectId | None = None, trigger: str = "scheduled"
) -> dict[str, Any]:
    """Clear both stores for every admin-tier account. Idempotent.

    `update_many` rather than a document loop: this is a field unset over
    a bounded set of rows, and one round trip per store keeps a manual
    click instant even with a year of audit history.
    """
    users = await _tier_users()
    ids = [u.id for u in users]
    if not ids:
        return {
            "accounts_cleared": 0,
            "audit_rows_cleared": 0,
            "trigger": trigger,
        }

    # `$ne: None` also excludes rows where the field was never written,
    # so modified_count is a true "how many actually carried an IP".
    users_res = await User.get_motor_collection().update_many(
        {"_id": {"$in": ids}, "last_login_ip": {"$ne": None}},
        {"$set": {"last_login_ip": None}},
    )
    audit_res = await AuditLog.get_motor_collection().update_many(
        {
            "user_id": {"$in": ids},
            "action": {"$in": LOGIN_ACTIONS},
            "ip_address": {"$ne": None},
        },
        {"$set": {"ip_address": None}},
    )

    summary = {
        "accounts_cleared": int(users_res.modified_count or 0),
        "audit_rows_cleared": int(audit_res.modified_count or 0),
        "accounts_scanned": len(ids),
        "trigger": trigger,
    }
    # Only a purge that actually removed something is worth a row. A
    # no-op run (second click, nothing stored) would otherwise move the
    # card's "Last cleared" stamp for a purge that cleared nothing.
    # Note the absence of `ip_address=` — recording the purger's own IP
    # here would re-create exactly what was just deleted.
    if summary["accounts_cleared"] or summary["audit_rows_cleared"]:
        await log_event(
            action=AuditAction.LOGIN_IP_PURGE,
            entity_type="AdminLoginIP",
            actor_id=actor_id,
            new_values=summary,
        )
    logger.info("admin_login_ip_purged", extra=summary)
    return summary


async def admin_ip_cleanup_loop(interval_sec: float = 300.0) -> None:
    """Purge once per IST day at `PURGE_AT`.

    Polls every five minutes rather than sleeping until midnight: a
    sleeping task that misses its wake-up (suspend, clock jump, leader
    hand-off mid-sleep) silently skips a day, while a poll + a persisted
    day marker always catches up on the next tick.

    On a database that has never purged there is no marker, so the first
    tick after boot purges immediately and the daily rhythm starts from
    there.
    """
    global _stop
    _stop = False
    logger.info(
        "admin_ip_cleanup_started",
        extra={"interval_sec": interval_sec, "purge_at_ist": PURGE_AT.strftime("%H:%M")},
    )

    from app.core.redis_client import cache_get, cache_set

    while not _stop:
        try:
            now = now_ist()
            day = now.strftime("%Y%m%d")
            rec = await cache_get(_LAST_DAY_KEY)
            last_day = str(rec.get("day")) if rec and rec.get("day") else None
            if last_day != day and now.time() >= PURGE_AT:
                # Claim the day BEFORE purging. `cache_set` raises once its
                # retries are spent, and the catch below swallows it — with
                # the marker written after the purge, a Redis blip left
                # `last_day` unset and the next tick five minutes later
                # purged again, wiping the IPs of everyone who signed in
                # since. Losing one day's purge is the cheaper failure.
                await cache_set(_LAST_DAY_KEY, {"day": day}, ttl_sec=_LAST_DAY_TTL)
                summary = await purge(trigger="scheduled")
                logger.info("admin_ip_cleanup_daily_done", extra=summary)
        except Exception:
            logger.exception("admin_ip_cleanup_loop_failed")
        try:
            await asyncio.sleep(interval_sec)
        except asyncio.CancelledError:
            return
