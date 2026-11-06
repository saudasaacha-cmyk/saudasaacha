"""MCX's close is derived from US daylight saving, not stored.

MCX's non-agri evening session ends 23:30 IST while US DST is in effect and
23:55 IST the rest of the year, flipping on the first trading day after each
US changeover. That used to be a hand-edited literal, copied into four places
that each do something different with it, and on 2026-11-02 the close moved
to 23:55 while the copies stayed behind. Every evening after that, until it
was fixed:

  • 23:30-23:55 — order entry refused with "MCX is closed" over a live session
  • 23:40-23:55 — the pending poller skipped MCX and the risk enforcer stopped
    firing stop-outs and brackets, because `is_after_close` said so
  • 23:41      — the EOD rollover swept MCX fourteen minutes early
  • after 23:30 — a silent Zerodha socket counted as healthy

Not one of those raises. They are silent no-ops, which is why a stale literal
survived a close-time change unnoticed.

So the value is now computed from the tz database. The test that matters is
`test_the_derivation_reproduces_every_circular_we_have` — if the rule ever
stops matching what MCX publishes, that is where it shows.

    pytest -q backend/tests/test_mcx_session_end.py
"""

from __future__ import annotations

import inspect
import pathlib
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.config import settings
from app.services import order_validator, zerodha_service
from app.services.position_service import intraday_to_carry_loop
from app.utils import time_utils as tu

REPO = pathlib.Path(__file__).resolve().parents[2]
PANEL = REPO / "frontend-user" / "lib" / "marketHours.ts"


def hhmm(t) -> tuple[int, int]:
    return (t.hour, t.minute)


def ist(y: int, m: int, d: int, hh: int = 23, mm: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=ZoneInfo("Asia/Kolkata"))


def src(module) -> str:
    return pathlib.Path(inspect.getfile(module)).read_text()


# ── the one that matters ─────────────────────────────────────────────
# Every MCX circular date we have, and what the exchange published for it.
# US DST 2026: began Sun 03-08, ended Sun 11-01. US DST 2027: begins Sun 03-14.
CIRCULARS = [
    ((2026, 3, 6), (23, 55), "Fri before US DST began"),
    ((2026, 3, 9), (23, 30), "first trading day after US DST began"),
    ((2026, 10, 30), (23, 30), "Fri before US DST ended"),
    ((2026, 11, 2), (23, 55), "first trading day after US DST ended"),
    ((2027, 3, 12), (23, 55), "last day of the 23:55 window per the circular"),
    ((2027, 3, 15), (23, 30), "first trading day after US DST begins again"),
]


@pytest.mark.parametrize("day,expected,why", CIRCULARS)
def test_the_derivation_reproduces_every_circular_we_have(day, expected, why):
    """If this fails, MCX has decoupled from US daylight saving and the
    derivation is no longer the authority — set `MCX_CLOSE_TIME` on the box to
    the published time while the rule is corrected."""
    assert hhmm(tu.mcx_session_end(ist(*day))) == expected, why


def test_the_changeovers_all_fall_on_a_non_trading_day():
    """Why the rule and the circular cannot disagree: every US changeover is a
    Sunday, so "US DST in effect" and "the first trading day the circular
    names" pick out the same sessions."""
    for (y, m, d), _, _ in CIRCULARS:
        assert datetime(y, m, d).weekday() != 6, "a circular date landed on a Sunday"


def test_only_the_two_published_values_are_ever_returned():
    """Swept across two full years of IST dates — a bug in the probe or the
    tz lookup would show up as some third time."""
    start = ist(2026, 1, 1)
    seen = {hhmm(tu.mcx_session_end(start + timedelta(days=n))) for n in range(730)}
    assert seen == {hhmm(tu.MCX_END_US_DST), hhmm(tu.MCX_END_US_STANDARD)}


# ── it has to be resolved per call, not per process ──────────────────
def test_the_session_end_is_a_function_not_a_constant():
    """The backend master routinely runs for days — it had five days of uptime
    when this was written. Anything resolved at import time would serve the
    pre-changeover close until somebody happened to restart, which is the
    whole failure being replaced here."""
    assert callable(tu.mcx_session_end)
    assert not hasattr(tu, "MCX_SESSION_END"), "a frozen constant is back"
    assert not hasattr(tu, "MCX_CLOSE"), "a frozen constant is back"


def test_the_close_lookup_threads_the_instant_through():
    """`is_after_close(seg, at)` must judge `at`'s own date, not today's —
    otherwise a backfill or a replayed instant gets the wrong session."""
    assert hhmm(tu.market_close_time_for_segment("MCX_FUT", ist(2026, 7, 1))) == (23, 30)
    assert hhmm(tu.market_close_time_for_segment("MCX_FUT", ist(2026, 12, 1))) == (23, 55)
    assert "market_close_time_for_segment(segment, at)" in src(tu)


# ── the escape hatch ─────────────────────────────────────────────────
def test_an_override_wins_outright(monkeypatch):
    monkeypatch.setattr(settings, "MCX_CLOSE_TIME", "22:15", raising=False)
    assert hhmm(tu.mcx_session_end(ist(2026, 7, 1))) == (22, 15)


def test_a_malformed_override_falls_back_to_the_derivation(monkeypatch):
    """A typo in an env var must not shut the session down."""
    monkeypatch.setattr(settings, "MCX_CLOSE_TIME", "not-a-time", raising=False)
    assert hhmm(tu.mcx_session_end(ist(2026, 12, 1))) == (23, 55)


def test_the_override_is_blank_by_default():
    """Shipped set, it would freeze the twice-yearly flip it exists to escape."""
    assert settings.MCX_CLOSE_TIME == ""


# ── the value that would disable the rollover ────────────────────────
def test_the_rollover_can_fire_at_either_close():
    """`intraday_to_carry_loop` fires the minute AFTER the close. At :59 that
    used to build minute 60, greater than every wall-clock time, so the
    group's rollover would never run again and never log a reason."""
    from app.services.carry_planner import rollover_fire_time

    for close in (tu.MCX_END_US_DST, tu.MCX_END_US_STANDARD, tu.NSE_BSE_CLOSE):
        fire = rollover_fire_time(close, 1)
        assert (fire.hour, fire.minute) <= (23, 59), (
            f"{close} makes the rollover minute unreachable"
        )
        # A :59 close rolls the HOUR rather than inventing minute 60.
        if close.minute == 59 and close.hour < 23:
            assert fire.hour == close.hour + 1 and fire.minute == 0


def test_the_loop_still_clamps_that_minute():
    """The clamp moved into `rollover_fire_time`, which does it with divmod.
    What must not come back is the loop doing its own minute arithmetic."""
    body = inspect.getsource(intraday_to_carry_loop)
    assert "rollover_fire_time(close_t" in body
    assert "close_t.minute + 1" not in body


def test_the_loop_resolves_the_close_against_now():
    body = inspect.getsource(intraday_to_carry_loop)
    assert "market_close_time_for_segment(next(iter(group_set)), now)" in body


# ── every consumer reads the function ────────────────────────────────
def test_the_new_order_gate_resolves_per_request():
    """The user-visible one: a stale close here turns traders away with "MCX
    is closed" while the exchange is still printing. The gate reaches
    `mcx_session_end` through `order_entry_close_for_segment`, which also
    folds in the admin's session override."""
    s = src(order_validator)
    assert "order_entry_close_for_segment(seg_upper, ist)" in s
    assert "_t(23, 30)" not in s and "_t(23, 55)" not in s
    # The old branch hard-coded MCX's OPEN as a local time(9, 0) too.
    assert "_t(9, 0)" not in s


def test_the_feed_health_window_resolves_per_call():
    s = src(zerodha_service)
    window = s[s.index("def _feed_expected_now") : s.index("def _find_account_entry_idx_locked")]
    assert "mcx_session_end(n)" in window
    assert "_dtime(23, 30)" not in window


def test_the_frontend_derives_it_the_same_way():
    """TypeScript cannot import the Python helper, so the rule is mirrored in
    `marketHours.ts`. Pin both values AND the DST read — a literal creeping
    back here shows "Market is closed" over a live session."""
    ts = PANEL.read_text()
    # Bounded at the function's own closing brace — a fixed character window
    # ran into the next helper and picked up its IST offset as a close time.
    start = ts.index("function _mcxSessionEndMinutes")
    helper = ts[start : ts.index("\n}", start)]
    assert '"America/New_York"' in helper and 'timeZoneName: "short"' in helper
    assert '"EDT"' in helper, "the frontend no longer reads the DST state"
    found = {
        (int(h), int(m)) for h, m in re.findall(r"(\d+) \* 60 \+ (\d+)", helper)
    }
    assert found == {hhmm(tu.MCX_END_US_DST), hhmm(tu.MCX_END_US_STANDARD)}, (
        f"marketHours.ts uses {found}, backend uses "
        f"{hhmm(tu.MCX_END_US_DST)} / {hhmm(tu.MCX_END_US_STANDARD)}"
    )


def test_the_frontend_branch_calls_the_helper():
    ts = PANEL.read_text()
    mcx = ts[ts.index('seg.startsWith("MCX")') :][:300]
    assert "_mcxSessionEndMinutes(now)" in mcx
    assert "23 * 60" not in mcx, "a literal close is back in the MCX branch"


# ── behaviour at the boundary, and the neighbours ────────────────────
def test_mcx_is_open_the_minute_before_its_close_and_shut_on_it():
    for (y, m, d), (hh, mm), _ in CIRCULARS:
        assert not tu.is_after_close("MCX_FUT", ist(y, m, d, hh, mm - 1))
        assert tu.is_after_close("MCX_FUT", ist(y, m, d, hh, mm))


def test_nse_is_untouched_by_any_of_this():
    assert hhmm(tu.NSE_BSE_CLOSE) == (16, 0)
    assert hhmm(tu.NSE_BSE_OPEN) == (9, 15)
    assert hhmm(tu.MCX_OPEN) == (9, 0)
    for (y, m, d), _, _ in CIRCULARS:
        assert hhmm(tu.market_close_time_for_segment("NFO_FUT", ist(y, m, d))) == (16, 0)


def test_mcx_morning_is_still_pre_open():
    """The guard that stopped the enforcer stopping-out against yesterday's
    last tick at 08:00. A close-time change must not touch it."""
    assert tu.is_before_open("MCX_FUT", ist(2026, 11, 2, 8, 0))
    assert not tu.is_before_open("MCX_FUT", ist(2026, 11, 2, 9, 30))


def test_forex_and_crypto_have_no_close_to_move():
    for seg in ("FOREX", "CRYPTO", "CDS"):
        assert tu.market_close_time_for_segment(seg) is None
        assert not tu.is_after_close(seg, ist(2026, 11, 2, 23, 59))
