"""Operator session overrides: the defaults are the floor, the rows only move them.

`time_utils` resolves every session gate synchronously from a module-level
snapshot that a per-worker loop pushes in. The direction matters more than the
feature: the code defaults stay authoritative and the rows merely override
them, so a worker that has never refreshed — or cannot reach Mongo at all —
behaves exactly as the platform did before this existed.

The alternative, the schedule living only in the collection, fails like this:
a cold worker resolves no close time, `market_close_time_for_segment` returns
None, `is_after_close` returns False for every segment, and the platform
decides the market never shuts. Parked orders fire and the risk enforcer books
stop-outs against an overnight tick, around the clock, silently. Half of this
file exists to pin that it cannot happen.

    pytest -q backend/tests/test_market_session_override.py
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.config import settings
from app.models.market_session import SESSION_GROUPS
from app.services import market_session_service as svc
from app.utils import time_utils as tu

MCX, NFO, CRYPTO, FOREX = "MCX_FUT", "NFO_FUT", "CRYPTO_SPOT", "CDS_FUTURE"


def ist(y=2026, m=11, d=3, hh=12, mm=0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=ZoneInfo("Asia/Kolkata"))


def hhmm(t):
    return None if t is None else (t.hour, t.minute)


@pytest.fixture(autouse=True)
def _clean_snapshot():
    """Every test starts from the cold-worker state and leaves it that way —
    the snapshot is module-level, so a leak would silently re-gate other
    tests' market hours."""
    tu.set_session_overrides({})
    yield
    tu.set_session_overrides({})


# ── the floor: no rows means no change ───────────────────────────────
def test_a_cold_worker_resolves_the_code_defaults():
    """The single most important assertion here. These are the values the
    platform used before overrides existed."""
    assert hhmm(tu.market_open_time_for_segment(NFO)) == (9, 15)
    assert hhmm(tu.market_close_time_for_segment(NFO, ist())) == (16, 0)
    assert hhmm(tu.market_open_time_for_segment(MCX)) == (9, 0)
    assert hhmm(tu.market_close_time_for_segment(MCX, ist())) == (23, 55)


def test_a_cold_worker_still_shuts_the_market():
    """`is_after_close` must not degrade to "never closes" — the failure the
    override direction exists to prevent."""
    assert tu.is_after_close(NFO, ist(hh=16, mm=1))
    assert tu.is_after_close(MCX, ist(hh=23, mm=56))


def test_session_less_segments_stay_session_less():
    for seg in (CRYPTO, FOREX):
        assert tu.session_group_for_segment(seg) is None
        assert tu.market_close_time_for_segment(seg, ist()) is None
        assert tu.market_open_time_for_segment(seg) is None


# ── overrides move the gates ─────────────────────────────────────────
def test_an_override_moves_the_nse_gate():
    tu.set_session_overrides({"NSE_BSE": {"open_time": "10:00", "gate_close": "17:15"}})
    assert hhmm(tu.market_open_time_for_segment(NFO)) == (10, 0)
    assert hhmm(tu.market_close_time_for_segment(NFO, ist())) == (17, 15)
    assert not tu.is_after_close(NFO, ist(hh=17, mm=14))
    assert tu.is_after_close(NFO, ist(hh=17, mm=15))


def test_an_override_moves_order_entry_separately_from_the_gate():
    """The two are different numbers on purpose — NSE's bell is 15:30 while
    its risk gate runs to 16:00. Overriding one must not drag the other."""
    tu.set_session_overrides({"NSE_BSE": {"entry_close": "14:00", "gate_close": "17:00"}})
    assert hhmm(tu.order_entry_close_for_segment(NFO, ist())) == (14, 0)
    assert hhmm(tu.market_close_time_for_segment(NFO, ist())) == (17, 0)


def test_a_partial_row_only_overrides_what_it_sets():
    tu.set_session_overrides({"MCX": {"open_time": "10:30"}})
    assert hhmm(tu.market_open_time_for_segment(MCX)) == (10, 30)
    assert hhmm(tu.market_close_time_for_segment(MCX, ist())) == (23, 55)


def test_an_override_for_one_group_leaves_the_other_alone():
    tu.set_session_overrides({"MCX": {"gate_close": "20:00"}})
    assert hhmm(tu.market_close_time_for_segment(MCX, ist())) == (20, 0)
    assert hhmm(tu.market_close_time_for_segment(NFO, ist())) == (16, 0)


def test_an_override_cannot_give_forex_a_close():
    """Giving a 24×5 segment a session would start squaring it off at a close
    it does not have."""
    tu.set_session_overrides({"NSE_BSE": {"gate_close": "17:00"}, "MCX": {"gate_close": "20:00"}})
    assert tu.market_close_time_for_segment(FOREX, ist()) is None
    assert tu.market_close_time_for_segment(CRYPTO, ist()) is None


# ── malformed rows must not take a gate down ─────────────────────────
@pytest.mark.parametrize("bad", ["", "   ", "garbage", "25:00", "9", None, "99:99"])
def test_a_malformed_override_falls_back_to_the_default(bad):
    tu.set_session_overrides({"NSE_BSE": {"gate_close": bad}})
    assert hhmm(tu.market_close_time_for_segment(NFO, ist())) == (16, 0)


def test_an_unknown_group_key_is_simply_ignored():
    tu.set_session_overrides({"NASDAQ": {"gate_close": "02:00"}})
    assert hhmm(tu.market_close_time_for_segment(NFO, ist())) == (16, 0)


# ── MCX precedence: env, then the admin pin, then DST ────────────────
def test_auto_dst_on_ignores_a_pinned_close():
    """`auto_dst` defaults to True, and while it is on the derivation wins —
    otherwise a forgotten pin would quietly freeze the twice-yearly flip."""
    tu.set_session_overrides({"MCX": {"entry_close": "21:00", "auto_dst": True}})
    assert hhmm(tu.mcx_session_end(ist())) == (23, 55)


def test_an_absent_auto_dst_flag_still_means_derive():
    """The DEFAULT, exercised without stating it — which is the case that
    actually occurs: an operator pins a close once, then clears the pin
    intending the twice-yearly flip to resume. If the absent flag defaulted to
    "off", that stale `entry_close` would win for ever and the March and
    November changeovers would silently stop happening. (A mutation flipping
    this default passed every other test in this file.)"""
    tu.set_session_overrides({"MCX": {"entry_close": "21:00"}})
    assert hhmm(tu.mcx_session_end(ist())) == (23, 55)


def test_turning_auto_dst_off_pins_the_close():
    tu.set_session_overrides({"MCX": {"entry_close": "21:00", "auto_dst": False}})
    assert hhmm(tu.mcx_session_end(ist())) == (21, 0)


def test_auto_dst_off_with_no_pin_still_derives():
    """Switching the toggle without filling the field must not resolve to
    nothing — that would be a None close, i.e. "MCX never shuts"."""
    tu.set_session_overrides({"MCX": {"auto_dst": False}})
    assert hhmm(tu.mcx_session_end(ist())) == (23, 55)


def test_the_env_hatch_outranks_the_admin_pin(monkeypatch):
    """`MCX_CLOSE_TIME` is set on the box by someone with SSH, for when the
    panel itself is wrong or unreachable. It has to win."""
    monkeypatch.setattr(settings, "MCX_CLOSE_TIME", "22:30", raising=False)
    tu.set_session_overrides({"MCX": {"entry_close": "21:00", "auto_dst": False}})
    assert hhmm(tu.mcx_session_end(ist())) == (22, 30)


# ── the refresher's two rules ────────────────────────────────────────
@pytest.mark.asyncio
async def test_a_failed_refresh_keeps_the_last_good_snapshot(monkeypatch):
    """A transient Mongo blip must not revert the platform to code defaults
    mid-session. That is a silent change to live risk gates."""
    tu.set_session_overrides({"NSE_BSE": {"gate_close": "17:00"}})

    async def boom(*_a, **_k):
        raise RuntimeError("mongo gone")

    monkeypatch.setattr(svc, "refresh_once", boom)
    task = asyncio.create_task(svc.market_session_refresh_loop(interval_sec=0.01))
    await asyncio.sleep(0.05)
    svc.stop_market_session_refresh()
    task.cancel()
    assert hhmm(tu.market_close_time_for_segment(NFO, ist())) == (17, 0)


def test_the_refresher_drops_groups_time_utils_cannot_resolve():
    """A stray row must not sit in the snapshot looking authoritative."""
    body = inspect.getsource(svc.refresh_once)
    assert "if r.group in SESSION_GROUPS" in body


def test_the_refresher_never_clears_on_error():
    body = inspect.getsource(svc.market_session_refresh_loop)
    assert "set_session_overrides" not in body, (
        "the loop must only install via refresh_once, never clear on the error path"
    )


def test_the_declared_groups_are_exactly_what_time_utils_understands():
    """`SESSION_GROUPS` gates what the refresher installs and what the admin
    panel offers. A name here that `session_group_for_segment` never returns
    would be an editable row that changes nothing."""
    resolvable = {
        tu.session_group_for_segment(s)
        for s in ("NSE_EQ", "NFO_FUT", "BSE_EQ", "BFO_OPT", "MCX_FUT", "MCX_OPT")
    }
    assert resolvable == set(SESSION_GROUPS)


# ── the open and the close must stay in lockstep ─────────────────────
def test_both_ends_of_the_window_resolve_through_one_group_lookup():
    """The grouping used to be written out twice, once per end. That is one
    edit away from a segment that opens on NSE's clock and closes on MCX's."""
    for fn in (tu.market_open_time_for_segment, tu.market_close_time_for_segment):
        assert "session_group_for_segment" in inspect.getsource(fn)


def test_every_indian_segment_name_resolves_to_a_group():
    """A name in the membership sets that no longer resolves would silently
    become session-less — permanently open, never rolled over."""
    for seg in sorted(tu.INDIAN_EQUITY_FNO_SEGMENTS | tu.MCX_SEGMENTS):
        assert tu.session_group_for_segment(seg) is not None, seg
        assert tu.market_close_time_for_segment(seg, ist()) is not None, seg


def test_no_rollover_exempt_segment_resolves_to_a_group():
    for seg in sorted(tu.ROLLOVER_EXEMPT_SEGMENTS):
        assert tu.session_group_for_segment(seg) is None, seg


def test_an_override_cannot_make_the_mcx_rollover_unreachable():
    """The rollover fires the minute AFTER the gate. A :59 gate used to build
    minute 60 and disable the sweep for good; the loop clamps, so an operator
    typing 23:59 degrades to firing on the close minute instead."""
    tu.set_session_overrides({"MCX": {"gate_close": "23:59"}})
    close = tu.market_close_time_for_segment(MCX, ist())
    assert hhmm(close) == (23, 59)
    fire_after = (close.hour, min(close.minute + 1, 59))
    assert fire_after <= (23, 59)
