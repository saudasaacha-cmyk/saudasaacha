"""WHEN the pre-close warning fires, and how often.

The shortfall arithmetic is pinned elsewhere. What this file guards is the
scheduling, which is where a warning feature actually goes wrong: firing twice,
firing on a day it already fired, firing after the gate has already run, or —
worst — not firing at all because a window was computed a minute too narrow and
the once-a-minute loop stepped straight over it.

    pytest -q backend/tests/test_carry_warning_schedule.py
"""

from __future__ import annotations

from datetime import datetime, time

import pytest

import app.services.position_service as ps
from app.api.v1.admin.settings import _parse_lead_minutes
from app.utils.time_utils import INDIAN_EQUITY_FNO_SEGMENTS

GROUP = "INDIAN_EQUITY_FNO"
CLOSE = time(16, 0)
DAY = "20261103"


@pytest.fixture(autouse=True)
def _clean():
    ps._last_warn_day.clear()
    yield
    ps._last_warn_day.clear()


@pytest.fixture
def fired(monkeypatch):
    """Capture what warn_carry_shortfalls was called with, without sending."""
    calls: list[dict] = []

    async def _fake(segment_set, *, group_label, deadline):
        calls.append({"label": group_label, "deadline": deadline})
        return len(calls)

    monkeypatch.setattr(ps, "warn_carry_shortfalls", _fake)
    return calls


def _row(leads):
    class _Row:
        warn_lead_minutes = leads

    return _Row()


@pytest.fixture
def leads(monkeypatch):
    """Install a market_sessions row without a database.

    Swaps the whole Document class rather than just `find_one`: Beanie builds
    `MarketSession.group` into a query expression only after `init_beanie`, so
    the argument would blow up before the patched method was ever reached.
    """

    def _install(values):
        import app.models.market_session as msm

        class _Stub:
            group = "group"  # makes `_Stub.group == x` a harmless bool

            @staticmethod
            async def find_one(*_a, **_k):
                return None if values is None else _row(values)

        monkeypatch.setattr(msm, "MarketSession", _Stub)

    return _install


async def _run(at: datetime):
    await ps._warn_before_close(
        GROUP, INDIAN_EQUITY_FNO_SEGMENTS, CLOSE, at, DAY, None
    )


def _at(h, m):
    return datetime(2026, 11, 3, h, m)


# ── the window ───────────────────────────────────────────────────────
async def test_it_fires_at_the_lead_mark(leads, fired):
    leads([30])
    await _run(_at(15, 30))
    assert len(fired) == 1
    assert fired[0]["deadline"] == "16:00"
    assert fired[0]["label"] == "NSE/BSE"


async def test_it_stays_quiet_before_the_mark(leads, fired):
    leads([30])
    await _run(_at(15, 29))
    assert fired == []


async def test_it_still_fires_a_minute_late(leads, fired):
    """The loop wakes once a minute and can drift. A window that is only the
    exact minute would be stepped over and the warning silently never sent."""
    leads([30])
    await _run(_at(15, 45))
    assert len(fired) == 1


async def test_it_does_not_fire_at_or_after_the_close(leads, fired):
    """At the bell the gate is about to run — a 'you have time' message then
    is worse than none."""
    leads([30])
    await _run(_at(16, 0))
    assert fired == []
    await _run(_at(16, 5))
    assert fired == []


# ── once per day, per lead ───────────────────────────────────────────
async def test_the_same_lead_fires_once_a_day(leads, fired):
    leads([30])
    for m in (30, 35, 40, 50):
        await _run(_at(15, m))
    assert len(fired) == 1


async def test_a_second_lead_is_its_own_ping(leads, fired):
    """30 gives time to move money, 10 is the last call. The later one must
    not be swallowed by the bookkeeping of the earlier."""
    leads([30, 10])
    await _run(_at(15, 30))
    await _run(_at(15, 50))
    assert len(fired) == 2


async def test_two_marks_missed_at_once_send_one_message(leads, fired):
    """Loop was down across both. Firing 30 and 10 back to back would deliver
    two identical messages a second apart."""
    leads([30, 10])
    await _run(_at(15, 55))
    assert len(fired) == 1
    # and both marks are spent, so the next tick stays quiet
    await _run(_at(15, 56))
    assert len(fired) == 1


async def test_tomorrow_fires_again(leads, fired):
    leads([30])
    await _run(_at(15, 30))
    assert len(fired) == 1
    ps._last_warn_day.clear()  # what a new day_key amounts to
    await _run(_at(15, 30))
    assert len(fired) == 2


# ── configuration ────────────────────────────────────────────────────
async def test_no_row_falls_back_to_the_shipped_default(leads, fired):
    """A fresh database must still warn, or the feature is off and nothing
    says so."""
    from app.models.market_session import DEFAULT_WARN_LEAD_MINUTES

    leads(None)
    lead = DEFAULT_WARN_LEAD_MINUTES[0]
    await _run(_at(CLOSE.hour - 1, 60 - lead))
    assert len(fired) == 1


async def test_an_empty_list_is_the_off_switch(leads, fired):
    leads([])
    for m in range(0, 60, 5):
        await _run(_at(15, m))
    assert fired == []


# ── the input an operator actually types ─────────────────────────────
def test_lead_minutes_parse_from_a_typed_string():
    assert _parse_lead_minutes("30, 10") == [30, 10]
    assert _parse_lead_minutes("10 30") == [30, 10]
    assert _parse_lead_minutes([10, 30]) == [30, 10]


def test_duplicates_collapse():
    assert _parse_lead_minutes("30, 30, 10") == [30, 10]


def test_blank_is_off_not_an_error():
    assert _parse_lead_minutes("") == []
    assert _parse_lead_minutes([]) == []
    assert _parse_lead_minutes(None) == []


@pytest.mark.parametrize("bad", ["abc", "30, x", "0", "241", "-5"])
def test_nonsense_is_rejected_rather_than_silently_dropped(bad):
    """Dropping a bad value would leave an empty list, which is the OFF state
    — a typo would turn the warning off and report success."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _parse_lead_minutes(bad)


def test_too_many_values_are_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _parse_lead_minutes("60,50,40,30,20")
