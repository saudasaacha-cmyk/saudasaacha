"""Push our clients into TeleCRM as leads.

One endpoint does everything: `POST {base}/enterprise/{id}/autoupdatelead`
creates or updates by the workspace's lead identifier, which is `phone`.
There is no batch endpoint — one request per lead, which is why the
backfill is paced rather than fanned out.

Three rules from TeleCRM that shape this file, none of them guessable from
the endpoint alone:

  * **never two requests in flight for the same phone.** Updates must land
    in order, so each lead takes a short Redis lock. Four gunicorn workers
    make this a cross-process problem, not an asyncio one.
  * **~5 requests/second**, which is the 18,000/hour budget spread evenly.
    Our steady state is nowhere near it; the backfill is, so the pacing
    gate is shared by both paths rather than bolted onto the loop.
  * **a 200 does not mean it landed.** Unknown field names, wrong types and
    a missing identifier are all dropped silently. So the response's
    `status` is logged, and the verification path goes through the Sync
    API, whose `remarks` array actually names what it ignored.

Only CLIENT-tier accounts become leads. Staff are not leads; the broker or
admin a client sits under rides along as `owner_*` fields instead.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from datetime import datetime
from typing import Any

import httpx

from app.core.redis_client import get_redis
from app.models.telecrm_settings import TeleCrmSettings
from app.models.user import User, UserRole, UserStatus
from app.services.user_service import is_placeholder_contact

logger = logging.getLogger(__name__)

ASYNC_BASE = "https://next-api.telecrm.in/enterprise"
SYNC_BASE = "https://next.telecrm.in/autoupdate/v2/enterprise"

# CLIENT, DEALER and MASTER are the trading tiers; the rest are staff.
LEAD_ROLES = {UserRole.CLIENT, UserRole.DEALER, UserRole.MASTER}

# TeleCRM's published ceiling is 5/sec (18,000/hour). Four is a deliberate
# margin: the counter below is per-second and a burst straddling a tick can
# otherwise land 10 inside one real second.
_MAX_PER_SEC = 4
_LOCK_TTL = 15
_HTTP_TIMEOUT = 20.0


# ── settings ────────────────────────────────────────────────────────
async def get_settings() -> TeleCrmSettings:
    s = await TeleCrmSettings.find_one()
    if s is None:
        s = TeleCrmSettings()
        await s.insert()
    return s


async def is_live() -> TeleCrmSettings | None:
    """The settings row when the integration is fully configured, else None.

    Callers treat None as "do nothing" — an unconfigured integration must
    never raise into a login or a registration.
    """
    s = await get_settings()
    if s.enabled and s.enterprise_id.strip() and s.async_token.strip():
        return s
    return None


# ── payload ─────────────────────────────────────────────────────────
def to_phone(mobile: str | None) -> str | None:
    """`91XXXXXXXXXX`, or None when there is nothing sendable.

    TeleCRM matches on a normalised phone, and a lead with no identifier is
    dropped SILENTLY while still answering 200 — so a number we cannot
    build is a lead we must not send at all, rather than one we send and
    assume landed.

    Placeholder contacts (`+000<user_code>`-shaped stand-ins for "no phone
    on file") are not numbers and are excluded here rather than at the call
    sites, so no caller has to remember.
    """
    raw = (mobile or "").strip()
    if not raw or is_placeholder_contact(raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        digits = f"91{digits}"
    # 12 digits == 91 + a 10-digit national number. Anything else is a
    # partial or malformed number, which is exactly what TeleCRM's Pitfalls
    # page says gets dropped.
    return digits if len(digits) == 12 and digits.startswith("91") else None


def _ms(dt: datetime | None) -> int | None:
    """Epoch MILLISECONDS, as a JSON number.

    Not ISO 8601, which TeleCRM does not parse and may store wrong or drop
    without saying so, and not a string — the number is what their date
    fields accept.
    """
    return int(dt.timestamp() * 1000) if dt is not None else None


def _owner_type(user: User, broker: User | None) -> str:
    if broker is None:
        return "Admin"
    # A broker with a parent broker is a sub-broker. Same distinction the
    # Active Users export makes, so the two screens agree.
    return "Sub-broker" if broker.assigned_broker_id else "Broker"


async def build_fields(
    user: User,
    *,
    online_since: int | None = None,
    owners: dict[Any, User] | None = None,
) -> dict[str, Any] | None:
    """The `fields` object for one user, or None when they cannot be sent.

    `owners` lets the backfill resolve admins and brokers once for the whole
    run instead of twice per user.
    """
    phone = to_phone(user.mobile)
    if phone is None:
        return None

    owners = owners if owners is not None else {}

    async def _owner(oid: Any) -> User | None:
        if oid is None:
            return None
        if oid not in owners:
            owners[oid] = await User.get(oid)
        return owners[oid]

    admin = await _owner(user.assigned_admin_id)
    broker = await _owner(user.assigned_broker_id)

    fields: dict[str, Any] = {
        "name": user.full_name or user.user_code,
        "phone": phone,
        "user_code": user.user_code,
        "owner_type": _owner_type(user, broker),
        "owner_admin": (admin.full_name or admin.user_code) if admin else "",
        "owner_broker": (broker.full_name or broker.user_code) if broker else "",
        "platform_status": user.status.value,
        "is_online": online_since is not None,
    }
    # A placeholder address is "no email on file", not an address — sending
    # it would plant a fake contact in the CRM.
    if user.email and not is_placeholder_contact(user.email):
        fields["email"] = user.email
    for key, value in (
        ("registered_at", _ms(user.created_at)),
        ("last_login_at", _ms(user.last_login_at)),
    ):
        if value is not None:
            fields[key] = value
    if online_since is not None:
        fields["online_since"] = online_since * 1000
    return fields


# ── pacing and per-lead serialisation ───────────────────────────────
async def _pace() -> None:
    """Hold the whole cluster under TeleCRM's per-second ceiling.

    A Redis counter per wall-clock second, because the four workers share
    one token's budget and an in-process semaphore would only ever see a
    quarter of the traffic. Degrades to "just send it" if Redis is down —
    at our volume that is well inside the limit, and a 429 is retryable
    anyway, so a cache outage should not stop the sync.
    """
    for _ in range(50):
        try:
            r = get_redis()
            key = f"telecrm:rate:{int(time.time())}"
            n = await r.incr(key)
            if n == 1:
                await r.expire(key, 2)
            if n <= _MAX_PER_SEC:
                return
        except Exception:  # pragma: no cover - pacing is not load-bearing
            return
        await asyncio.sleep(0.25)


async def _send(
    s: TeleCrmSettings, fields: dict[str, Any], *, assignee: str | None = None
) -> tuple[bool, str]:
    """One create-or-update. Returns (ok, detail).

    The per-phone lock is the point: TeleCRM asks that two requests for the
    same identifier never overlap, so a user who logs in while a reconcile
    is mid-flight does not race their own row.
    """
    body: dict[str, Any] = {"fields": dict(fields)}
    if assignee:
        body["fields"]["assignee"] = assignee

    lock_key = f"telecrm:lead:{fields['phone']}"
    got = False
    try:
        r = get_redis()
        got = bool(await r.set(lock_key, "1", ex=_LOCK_TTL, nx=True))
        if not got:
            # Someone else is mid-write for this lead. Theirs carries the
            # same or newer state, so dropping this one is correct rather
            # than merely convenient.
            return True, "skipped: another write in flight"
    except Exception:  # pragma: no cover
        logger.debug("telecrm_lock_unavailable", exc_info=True)

    try:
        await _pace()
        url = f"{ASYNC_BASE}/{s.enterprise_id.strip()}/autoupdatelead"
        headers = {
            "Authorization": f"Bearer {s.async_token.strip()}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for attempt in range(3):
                resp = await client.post(url, json=body, headers=headers)
                if resp.status_code == 429:
                    # Documented as "back off and retry"; create-or-update
                    # on an identifier is idempotent, so a retry is safe.
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code == 403:
                    return False, "403 NOT_AUTHORIZED — is this an Async token?"
                if resp.status_code >= 400:
                    return False, f"{resp.status_code} {resp.text[:160]}"
                # 200 is lead-level only: dropped fields are not reported.
                try:
                    data = resp.json()
                except ValueError:
                    data = {}
                return True, str(data.get("status") or "OK")
        return False, "429 after 3 attempts"
    except Exception as exc:  # pragma: no cover - network
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        if got:
            # The lock has a TTL, so a failed release costs at most
            # `_LOCK_TTL` of not writing this one lead again — not worth
            # a log line on every Redis blip.
            with contextlib.suppress(Exception):
                await get_redis().delete(lock_key)


# ── the one entry point the rest of the app uses ────────────────────
async def push_user(user: User | Any, *, online_since: int | None = None) -> bool:
    """Sync one user. Never raises — callers are logins and registrations.

    Returns False for "not sent", which covers a disabled integration, a
    staff account, and a client with no real phone. None of those are
    errors and none of them should read as one in a log.
    """
    try:
        s = await is_live()
        if s is None:
            return False
        if not isinstance(user, User):
            user = await User.get(user)
            if user is None:
                return False
        if user.role not in LEAD_ROLES or user.is_demo:
            return False

        fields = await build_fields(user, online_since=online_since)
        if fields is None:
            return False

        ok, detail = await _send(s, fields)
        s.last_push_at = datetime.now().astimezone()
        if ok:
            s.pushed_total += 1
        else:
            s.failed_total += 1
            s.last_error = detail[:300]
            logger.warning("telecrm_push_failed user=%s %s", user.user_code, detail)
        await s.save()
        return ok
    except Exception:  # pragma: no cover - must never break a login
        logger.exception("telecrm_push_crashed")
        return False


def push_user_bg(user: User | Any, *, online_since: int | None = None) -> None:
    """Fire-and-forget wrapper for request paths.

    Held in a set because `create_task` keeps only a weak reference, so an
    unreferenced task can be collected mid-flight and the push would just
    stop with nothing logged.
    """
    task = asyncio.create_task(push_user(user, online_since=online_since))
    _BG.add(task)
    task.add_done_callback(_BG.discard)


_BG: set[asyncio.Task] = set()


# ── backfill / reconcile ────────────────────────────────────────────
async def sync_all(*, limit: int | None = None) -> dict[str, int]:
    """Every sendable client, paced. Used by the backfill button and the
    nightly reconcile.

    Deliberately sequential: there is no batch endpoint, the per-second gate
    is the real constraint, and ~680 leads takes two to four minutes, which
    is nobody's emergency.
    """
    s = await is_live()
    if s is None:
        return {"sent": 0, "skipped": 0, "failed": 0}

    owners: dict[Any, User] = {}
    sent = skipped = failed = 0
    query = {
        "role": {"$in": [r.value for r in LEAD_ROLES]},
        "status": {"$ne": UserStatus.CLOSED.value},
        "is_demo": {"$ne": True},
    }
    users = await User.find(query).to_list()
    if limit:
        users = users[:limit]

    for user in users:
        fields = await build_fields(user, owners=owners)
        if fields is None:
            skipped += 1
            continue
        ok, detail = await _send(s, fields)
        if ok:
            sent += 1
        else:
            failed += 1
            s.last_error = detail[:300]

    s.last_push_at = datetime.now().astimezone()
    s.pushed_total += sent
    s.failed_total += failed
    await s.save()
    logger.info("telecrm_sync_all sent=%d skipped=%d failed=%d", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}


# ── verification ────────────────────────────────────────────────────
async def test_connection() -> tuple[bool, str]:
    """Prove the credentials work without inventing a lead.

    Prefers the Sync API's read-only `GET /metadata`, which also tells us
    the workspace's lead identifier. Falls back to reporting that no
    read-only check is possible — the Async endpoint's only "test" is to
    write a lead, and a connection test that leaves junk in the CRM is not
    a test anyone wants to press twice.
    """
    s = await get_settings()
    eid = s.enterprise_id.strip()
    missing = [
        msg
        for ok, msg in (
            (eid, "No enterprise ID set."),
            (s.async_token.strip(), "No Async token set."),
            (
                s.sync_token.strip(),
                "Add a Sync token to test. The Async endpoint can only be "
                "checked by writing a lead, which would leave a real row "
                "in your CRM.",
            ),
        )
        if not ok
    ]
    if missing:
        return False, " ".join(missing)
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(
                f"{SYNC_BASE}/{eid}/metadata",
                headers={"Authorization": f"Bearer {s.sync_token.strip()}"},
            )
        if resp.status_code == 401:
            return False, "401 NOT_AUTHORIZED — is this a Sync token?"
        if resp.status_code >= 400:
            return False, f"{resp.status_code} {resp.text[:200]}"
        data = resp.json() if resp.text else {}
        ident = data.get("leadIdentifierFieldId") or "unknown"
        return True, f"Connected. Lead identifier field: {ident}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


async def reconcile_loop(interval_sec: float = 21600.0) -> None:
    """Re-push every client on a cadence, so the CRM does not drift.

    Six hours rather than nightly. The columns that go stale are the ones
    with no event behind them: `is_online` has no offline event to hook
    (presence is a Redis key that simply expires — see `presence_service`),
    and a client renamed or moved between brokers changes nothing we watch.
    A daily job would leave those wrong for most of a day; four runs cost
    ~2,700 requests against an 18,000/hour budget, so the cheap answer wins.

    Leader-gated by the caller, so exactly one worker runs it. Each pass is
    paced to TeleCRM's per-second ceiling and takes two to four minutes.
    """
    while True:
        try:
            if await is_live() is not None:
                await sync_all()
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - the loop must outlive a bad run
            logger.exception("telecrm_reconcile_failed")
        await asyncio.sleep(interval_sec)
