"""The bad-tick filter must block garbage without blocking the market.

Measured on production 2026-11-05 with the market open: the old rule —
"reject any tick more than 50% from the last one" — fired 2,629 times in a
morning and left nine of ten sampled strikes reading 0.00 while Kite quoted
them normally. A deep option doubles or halves on one trade; that is the
market, not a glitch.

    pytest -q backend/tests/test_bad_tick_filter.py
"""

from __future__ import annotations

from app.services.zerodha_service import is_bad_tick


def test_a_real_option_move_is_not_garbage():
    """SENSEX 79400PE: 1251.70 -> 564.65, inside a day range of 492-1251.70.
    Both prices traded today; the jump is the instrument, not the feed."""
    assert not is_bad_tick(564.65, 1251.70, 1.0, 492.0, 1251.70)


def test_an_option_that_traded_once_all_day():
    """FINNIFTY 25300CE: day low == high == 899.15. The old rule rejected
    every tick of it, so our price stayed 0.00 against Kite's 899.15."""
    assert not is_bad_tick(899.15, 525.5, 1.0, 899.15, 899.15)


def test_garbage_far_below_the_day_range_is_still_rejected():
    """The tick that phantom-closed positions: NIFTY BANK at Rs 28 while the
    day's low was 57,800."""
    assert is_bad_tick(28.0, 58000.0, 1.0, 57800.0, 58400.0)


def test_garbage_far_above_the_day_range_is_still_rejected():
    assert is_bad_tick(120.0, 71.0, 1.0, 70.2, 71.9)


def test_a_new_extreme_is_allowed_through_the_slack():
    """The tick that SETS a new high can arrive before the OHLC that
    includes it — 5% of slack keeps it from being refused."""
    assert not is_bad_tick(74.0, 48.0, 1.0, 47.0, 71.9)


def test_without_ohlc_the_jump_rule_still_applies():
    """LTP-mode ticks carry no band; fall back to the old behaviour rather
    than trusting everything."""
    assert is_bad_tick(564.65, 1251.70, 1.0, 0.0, 0.0)


def test_an_old_baseline_never_condemns_a_tick():
    """Past the staleness window a big move is believable — an illiquid
    strike that has not printed for a minute must not stay frozen."""
    assert not is_bad_tick(28.0, 58000.0, 45.0, 57800.0, 58400.0)


def test_small_moves_and_missing_prices_are_untouched():
    assert not is_bad_tick(57119.0, 57110.0, 0.2, 57000.0, 57200.0)
    assert not is_bad_tick(0.0, 57110.0, 0.2, 57000.0, 57200.0)
    assert not is_bad_tick(57119.0, 0.0, 0.2, 57000.0, 57200.0)
