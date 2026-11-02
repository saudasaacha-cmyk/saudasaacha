"""The admin market-status screen must never be able to disagree with the gates.

A status screen that re-derives the schedule locally is worse than no screen:
it reassures you about a gate that is actually mis-set. The 2026-11-02 MCX
drift — order entry refusing at 23:30 and the risk enforcer going quiet at
23:40 against a 23:55 session, every evening, silently — is exactly the kind
of thing it exists to show, and it can only show it by asking the same
helpers the trading paths ask.

So these pin two things: the states it reports at each boundary, and that it
reports them by CALLING `is_before_open` / `is_after_close` /
`is_within_open_grace` rather than comparing clock times itself.

    pytest -q backend/tests/test_market_status.py
"""

from __future__ import annotations

import inspect
import re
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.api.v1.admin import market
from app.core.config import settings
from app.utils.time_utils import (
    market_close_time_for_segment,
    market_open_time_for_segment,
)

MCX = "MCX_FUT"
NFO = "NFO_FUT"
CRYPTO = "CRYPTO_SPOT"


def ist(y: int, m: int, d: int, hh: int, mm: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=ZoneInfo("Asia/Kolkata"))


def ctx(probe: str, now: datetime, *, holiday=None, weekend=False) -> dict:
    """The context the handler builds for one group."""
    open_t = market_open_time_for_segment(probe)
    gate_t = market_close_time_for_segment(probe, now)
    return {
        "holiday": holiday,
        "weekend": weekend,
        "always_on": open_t is None and gate_t is None,
        "open_t": open_t,
        "gate_t": gate_t,
    }


def state(probe: str, now: datetime, **kw) -> str:
    return market._session_state(probe, now, ctx(probe, now, **kw))[0]


# ── the states, at the boundaries that matter ────────────────────────
# 2026-11-03 is a Tuesday; MCX runs 09:00-23:55 after the 11-02 circular.
@pytest.mark.parametrize(
    "hh,mm,expected",
    [
        (8, 0, "PRE_OPEN"),
        (9, 0, "SETTLING"),   # the 60 s hold after the bell
        (9, 2, "OPEN"),
        (23, 54, "OPEN"),     # the fifteen minutes the old literal got wrong
        (23, 55, "CLOSED"),
    ],
)
def test_mcx_through_its_day(hh, mm, expected):
    assert state(MCX, ist(2026, 11, 3, hh, mm)) == expected


@pytest.mark.parametrize(
    "hh,mm,expected",
    [(8, 0, "PRE_OPEN"), (9, 16, "OPEN"), (15, 59, "OPEN"), (16, 0, "CLOSED")],
)
def test_nse_through_its_day(hh, mm, expected):
    """NSE's reported close is the RISK GATE (16:00), not the 15:30 bell — the
    two are different on purpose and the screen shows both columns."""
    assert state(NFO, ist(2026, 11, 3, hh, mm)) == expected


def test_crypto_is_always_open_even_at_a_weekend_midnight():
    assert state(CRYPTO, ist(2026, 11, 1, 3, 0), weekend=True) == "OPEN"


def test_a_weekend_beats_the_clock():
    assert state(MCX, ist(2026, 11, 1, 12, 0), weekend=True) == "WEEKEND"


def test_a_full_day_holiday_beats_the_clock():
    hol = SimpleNamespace(is_full_day=True, description="Diwali")
    s, note = market._session_state(
        MCX, ist(2026, 11, 3, 12, 0), ctx(MCX, ist(2026, 11, 3, 12, 0), holiday=hol)
    )
    assert (s, note) == ("HOLIDAY", "Diwali")


def test_a_partial_day_holiday_does_not_claim_the_market_is_shut():
    """A partial-day row carries its own window and the validator honours it;
    reporting HOLIDAY here would contradict a session that is in fact open."""
    hol = SimpleNamespace(is_full_day=False, description="Muhurat", open_time="18:00")
    assert state(MCX, ist(2026, 11, 3, 12, 0), holiday=hol) == "OPEN"


def test_the_gates_are_reported_in_the_order_they_actually_apply():
    """Weekend outranks pre-open, holiday outranks the clock. If the table is
    reordered the screen starts naming the wrong reason for a refusal."""
    src = inspect.getsource(market._session_state)
    order = [src.index(f'"{s}"') for s in ("WEEKEND", "HOLIDAY", "PRE_OPEN", "CLOSED", "SETTLING")]
    assert order == sorted(order)


# ── it must ask, not re-derive ───────────────────────────────────────
def test_the_screen_calls_the_production_predicates():
    src = inspect.getsource(market)
    for fn in ("is_before_open", "is_after_close", "is_within_open_grace", "is_weekend"):
        assert f"{fn}(" in src, f"{fn} is not being consulted"


def test_the_screen_does_not_hard_code_any_session_time():
    """The whole value of the page is that it cannot be wrong independently of
    the platform. A literal clock time here breaks that."""
    # The module's prose cites the 23:30 / 23:40 / 23:55 incident by name, so
    # strip docstrings before judging — comments and docstrings cannot drift
    # out of step with a gate, only code can.
    code = re.sub(r'"""[\s\S]*?"""', "", inspect.getsource(market))
    bad = re.findall(r"\btime\(\s*\d+\s*,", code) + re.findall(
        r"\b(?:09|15|23):[0-5]\d\b", code
    )
    assert not bad, f"hard-coded session times in the status screen: {bad}"


def test_mcx_entry_close_follows_daylight_saving():
    """Not a copy of it — the same `mcx_session_end` the order gate calls."""
    assert market._entry_close(MCX, ist(2026, 7, 1, 12), False)[0].strftime("%H:%M") == "23:30"
    assert market._entry_close(MCX, ist(2026, 12, 1, 12), False)[0].strftime("%H:%M") == "23:55"


def test_nse_entry_close_comes_from_the_env_the_validator_reads():
    close, source = market._entry_close(NFO, ist(2026, 11, 3, 12), False)
    assert close.strftime("%H:%M") == settings.MARKET_CLOSE_TIME
    assert "MARKET_CLOSE_TIME" in source


def test_an_unparseable_env_close_says_so_instead_of_claiming_a_time(monkeypatch):
    monkeypatch.setattr(settings, "MARKET_CLOSE_TIME", "garbage", raising=False)
    close, source = market._entry_close(NFO, ist(2026, 11, 3, 12), False)
    assert close is None and "unparseable" in source


# ── shape ────────────────────────────────────────────────────────────
def test_every_group_probes_a_segment_the_helpers_recognise():
    """A typo in a probe string would make the helpers fall through to None and
    the group would silently render as 24×7 — permanently "OPEN"."""
    for g in market._GROUPS:
        probe = g["probe"]
        resolved = (
            market_open_time_for_segment(probe),
            market_close_time_for_segment(probe),
        )
        if g["group"] in ("Forex (CDS)", "Crypto"):
            assert resolved == (None, None), f"{probe} should be session-less"
        else:
            assert all(r is not None for r in resolved), f"{probe} is unrecognised"


def test_the_screen_is_read_only():
    """It reports gates; it must never change one. A write here would make a
    diagnostic page a way to move a live risk boundary."""
    src = inspect.getsource(market)
    for w in (".save(", ".insert(", ".update(", ".delete(", "@router.post", "@router.put"):
        assert w not in src, f"{w} in a read-only status module"


# ── it has to render when everything is broken ───────────────────────
@pytest.mark.asyncio
async def test_the_handler_survives_every_dependency_being_down():
    """The page is most useful exactly when the feed is dead, Redis is
    unreachable or Mongo is not initialised — so none of those may raise. Each
    one degrades to an "unavailable" row while the session table, which needs
    nothing but the clock, still renders."""
    res = await market.market_status(admin=SimpleNamespace(role="SUPER_ADMIN"))
    data = res.data

    assert data["now_ist"] and data["weekday"]
    assert len(data["segments"]) == len(market._GROUPS)
    for seg in data["segments"]:
        assert seg["state"] in {
            "OPEN", "CLOSED", "PRE_OPEN", "SETTLING", "WEEKEND", "HOLIDAY"
        }
        assert set(seg) >= {"group", "state", "opens", "risk_gate_closes", "close_source"}
    # Feeds and locks are allowed to be unavailable; they are not allowed to
    # take the page down with them.
    assert isinstance(data["feeds"], list)
    assert isinstance(data["leaders"], list)
