"""The admin login-IP card and its daily purge, at the two points that broke.

No database: `stats` and `purge` touch exactly two collections and one
audit writer, so stubbing those three is cheaper than standing up a
replica set for a field unset.

    pytest -q backend/tests/test_admin_ip_purge.py
"""

from __future__ import annotations

import inspect
from datetime import datetime
from types import SimpleNamespace

from app.services import admin_ip_cleanup_service as svc
from app.utils.time_utils import UTC


class _Collection:
    """Stands in for a motor collection: counts, and reports back how many
    rows an `update_many` touched."""

    def __init__(self, *, count: int = 0, modified: int = 0) -> None:
        self._count = count
        self._modified = modified
        self.filters: list[dict] = []

    # `AuditLog.find(...).sort(...).limit(...).to_list()` / `.count()`
    def find(self, flt: dict):
        self.filters.append(flt)
        return self

    async def count(self) -> int:
        return self._count

    def get_motor_collection(self):
        return self

    async def update_many(self, flt: dict, _update: dict):
        self.filters.append(flt)
        return SimpleNamespace(modified_count=self._modified)


def _admin(ip: str | None, last_login_at: datetime | None) -> SimpleNamespace:
    return SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        user_code="AD0001",
        full_name="An Admin",
        role="ADMIN",
        last_login_ip=ip,
        last_login_at=last_login_at,
    )


def _patch(monkeypatch, users, *, modified=(0, 0), audit_count=0):
    calls: list[dict] = []
    monkeypatch.setattr(svc, "_tier_users", lambda: _async(users))
    monkeypatch.setattr(svc, "_last_purge_at", lambda: _async(None))
    monkeypatch.setattr(svc, "User", _Collection(modified=modified[0]))
    monkeypatch.setattr(
        svc, "AuditLog", _Collection(count=audit_count, modified=modified[1])
    )
    monkeypatch.setattr(svc, "log_event", lambda **kw: _async(calls.append(kw)))
    return calls


async def _async(value):
    return value


async def test_stats_survives_an_admin_row_with_an_ip_but_no_login_timestamp(monkeypatch):
    """The 500 on both super-admin endpoints. Motor is built tz_aware, so
    `last_login_at` comes back offset-aware; the naive sentinel it was sorted
    against raised TypeError the moment one row's timestamp was null."""
    _patch(
        monkeypatch,
        [_admin("1.2.3.4", None), _admin("5.6.7.8", datetime.now(UTC))],
    )
    out = await svc.stats()
    assert out["accounts_with_ip"] == 2
    # Newest login first, and the row that has none sorts last rather than
    # taking the endpoint down with it.
    assert out["samples"][0]["ip"] == "5.6.7.8"


def test_the_sort_sentinel_is_offset_aware():
    """Naive again and every null `last_login_at` is a 500 again."""
    assert svc._NEVER.tzinfo is not None
    assert datetime.now(UTC) > svc._NEVER


async def test_a_purge_that_cleared_nothing_writes_no_audit_row(monkeypatch):
    """"Last cleared <timestamp>" on the card is read back off this row, so a
    no-op run that logged one claimed a purge that removed nothing."""
    calls = _patch(monkeypatch, [_admin(None, None)], modified=(0, 0))
    summary = await svc.purge(trigger="manual")
    assert summary["accounts_cleared"] == 0
    assert summary["audit_rows_cleared"] == 0
    assert calls == []


async def test_a_purge_that_cleared_something_still_writes_the_row(monkeypatch):
    """Clearing the trail has to leave a trail — the guard above must not
    silence a real purge."""
    calls = _patch(monkeypatch, [_admin("1.2.3.4", None)], modified=(1, 0))
    await svc.purge(trigger="manual")
    assert len(calls) == 1
    assert calls[0]["action"] is svc.AuditAction.LOGIN_IP_PURGE
    # Recording the purger's own IP would re-create what was just deleted.
    assert calls[0].get("ip_address") is None


def test_the_day_marker_is_claimed_before_the_purge_runs():
    """`cache_set` raises once its retries are spent and the loop's broad
    `except` swallows it. Written after the purge, that blip left the marker
    unset and the next five-minute tick purged again — up to 288 times a day,
    each one wiping the IPs of everyone who signed in since."""
    src = inspect.getsource(svc.admin_ip_cleanup_loop)
    assert src.index("cache_set(_LAST_DAY_KEY") < src.index("await purge(")
