"""The MCX trade-end is one fact, and it used to live in six places.

MCX's non-agri close moves twice a year with US daylight saving — 23:30 IST
while US DST is in effect, 23:55 IST otherwise — so this value is edited
roughly every March and November, from an exchange circular.

It was copied as a literal into the rollover gate, the new-order gate, the
feed-health window and the frontend's market-hours table. On 2026-11-02 the
close moved to 23:55 and those copies did not move together: the rollover
gate still read 23:40, so for the fifteen minutes between 23:40 and 23:55 —
with MCX live and printing — the pending-order poller skipped every MCX
order and the risk enforcer stopped firing stop-outs, while the new-order
gate turned users away at 23:30 with "MCX is closed".

Nothing raised. Every one of those is a silent no-op.

So these tests pin the invariants rather than the number: one source of
truth, every consumer reading it, and the one value that would disable the
rollover outright.

    pytest -q backend/tests/test_mcx_session_end.py
"""

from __future__ import annotations

import inspect
import pathlib
import re
from datetime import datetime, time

from app.services import order_validator, zerodha_service
from app.services.position_service import intraday_to_carry_loop
from app.utils import time_utils as tu

REPO = pathlib.Path(__file__).resolve().parents[2]


def src(module) -> str:
    return pathlib.Path(inspect.getfile(module)).read_text()


def hhmm(t: time) -> tuple[int, int]:
    return (t.hour, t.minute)


# ── one source of truth ──────────────────────────────────────────────
def test_the_rollover_gate_sits_on_the_session_end():
    """Not a copy of it, and not a buffer past it — see the constant's own
    comment for why MCX cannot take NSE's 30-minute one."""
    assert tu.MCX_CLOSE == tu.MCX_SESSION_END


def test_the_session_end_is_one_of_the_two_values_the_circular_uses():
    """A guard against a typo in the twice-yearly edit: 2:55 and 23:05 would
    both quietly shut MCX trading for most of the day."""
    assert hhmm(tu.MCX_SESSION_END) in ((23, 30), (23, 55)), (
        f"{tu.MCX_SESSION_END} is neither MCX close — US-DST 23:30 nor 23:55"
    )


def test_nse_is_untouched_by_this():
    assert hhmm(tu.NSE_BSE_CLOSE) == (16, 0)
    assert hhmm(tu.NSE_BSE_OPEN) == (9, 15)
    assert hhmm(tu.MCX_OPEN) == (9, 0)


# ── the value that would disable the rollover ────────────────────────
def test_the_rollover_can_actually_fire_at_this_close():
    """`intraday_to_carry_loop` fires the minute AFTER the close. At :59 that
    used to build minute 60, which is greater than every wall-clock time, so
    the group's rollover would never run again — no MIS->NRML, no EOD
    square-off, and not one line in the log to say so."""
    fire_after = (tu.MCX_CLOSE.hour, min(tu.MCX_CLOSE.minute + 1, 59))
    assert fire_after <= (23, 59), "the rollover minute is unreachable"
    assert fire_after > (tu.MCX_CLOSE.hour, tu.MCX_CLOSE.minute - 1)


def test_the_loop_still_clamps_that_minute():
    """The clamp is what makes the test above true for ANY close, including a
    future circular that lands on :59."""
    body = inspect.getsource(intraday_to_carry_loop)
    assert "min(close_t.minute + 1, 59)" in body, "minute-60 landmine is back"


# ── every consumer reads the one name ────────────────────────────────
def test_the_new_order_gate_reads_the_constant():
    """This is the user-visible one: a stale literal here turns traders away
    with "MCX is closed" while the exchange is still open."""
    s = src(order_validator)
    assert "MCX_SESSION_END" in s
    assert "_t(23, 30)" not in s and "_t(23, 55)" not in s


def test_the_feed_health_window_reads_the_constant():
    s = src(zerodha_service)
    window = s[s.index("def _feed_expected_now") : s.index("def _find_account_entry_idx_locked")]
    assert "MCX_SESSION_END" in window
    assert "_dtime(23, 30)" not in window


def test_the_frontend_table_matches_the_backend():
    """TypeScript cannot import the Python constant, so the copy in
    `marketHours.ts` is pinned here instead. This is the assertion that
    actually catches the drift — the other copies are now derived."""
    ts = (REPO / "frontend-user" / "lib" / "marketHours.ts").read_text()
    mcx = ts[ts.index('seg.startsWith("MCX")') :][:400]
    m = re.search(r"min <= (\d+) \* 60 \+ (\d+)", mcx)
    assert m, "could not find the MCX close expression in marketHours.ts"
    assert (int(m.group(1)), int(m.group(2))) == hhmm(tu.MCX_SESSION_END), (
        "marketHours.ts disagrees with time_utils.MCX_SESSION_END — "
        "the UI will show MCX closed while the backend accepts orders, or vice versa"
    )


# ── behaviour at the boundary ────────────────────────────────────────
def _at(h: int, m: int) -> datetime:
    """A Monday, in IST."""
    return tu.to_ist(datetime(2026, 11, 2, h, m, tzinfo=tu.IST))


def test_mcx_is_open_the_minute_before_its_close():
    before = (tu.MCX_CLOSE.hour, tu.MCX_CLOSE.minute - 1)
    assert not tu.is_after_close("MCX_FUT", _at(*before))
    assert not tu.is_before_open("MCX_FUT", _at(*before))


def test_mcx_is_closed_from_its_close_minute():
    assert tu.is_after_close("MCX_FUT", _at(tu.MCX_CLOSE.hour, tu.MCX_CLOSE.minute))


def test_mcx_morning_is_still_pre_open():
    """The guard that stopped the enforcer stopping-out against yesterday's
    last tick at 08:00 — unaffected by a close-time change, pinned so it
    stays that way."""
    assert tu.is_before_open("MCX_FUT", _at(8, 0))
    assert not tu.is_before_open("MCX_FUT", _at(9, 30))


def test_forex_and_crypto_have_no_close_to_move():
    for seg in ("FOREX", "CRYPTO", "CDS"):
        assert tu.market_close_time_for_segment(seg) is None
        assert not tu.is_after_close(seg, _at(23, 59))
