"""No new price for N seconds → no new trades on that instrument.

A 60-second version of this was removed in July 2026 for false-blocking during
feed hiccups, so the rules that keep it from doing that again are the point of
these tests: it is off by default at 0, silent when there is nothing to judge,
and inactive while the feed is still warming up after a reconnect.

    pytest -q backend/tests/test_stale_feed_block.py
"""

from __future__ import annotations

from app.services.order_validator import stale_feed_block_reason


def test_blocks_when_the_price_has_not_moved_past_the_limit():
    msg = stale_feed_block_reason(
        symbol="CRUDEOIL", price_age_sec=45, threshold_sec=30, feed_warm_age_sec=600
    )
    assert msg is not None
    assert "CRUDEOIL" in msg and "45s" in msg


def test_allows_a_price_inside_the_limit():
    assert (
        stale_feed_block_reason(
            symbol="X", price_age_sec=29.9, threshold_sec=30, feed_warm_age_sec=600
        )
        is None
    )


def test_zero_turns_the_feature_off():
    assert (
        stale_feed_block_reason(
            symbol="X", price_age_sec=9999, threshold_sec=0, feed_warm_age_sec=600
        )
        is None
    )


def test_no_price_age_never_blocks():
    # Nothing to judge by — an instrument with no exchange timestamp at all
    # must not be blocked by this rule.
    assert (
        stale_feed_block_reason(
            symbol="X", price_age_sec=None, threshold_sec=30, feed_warm_age_sec=600
        )
        is None
    )


def test_warm_up_after_a_reconnect_suspends_the_block():
    # Right after a deploy every instrument looks quiet; freezing the whole
    # platform for a minute is the failure this grace period exists to avoid.
    assert (
        stale_feed_block_reason(
            symbol="X", price_age_sec=300, threshold_sec=30, feed_warm_age_sec=5
        )
        is None
    )


def test_block_resumes_once_the_grace_period_has_passed():
    msg = stale_feed_block_reason(
        symbol="X", price_age_sec=300, threshold_sec=30, feed_warm_age_sec=61
    )
    assert msg is not None


def test_unknown_feed_warm_time_still_blocks():
    # No warm-up marker (Redis cold) must not become a way to bypass the rule.
    msg = stale_feed_block_reason(
        symbol="X", price_age_sec=120, threshold_sec=30, feed_warm_age_sec=None
    )
    assert msg is not None


# ── Binance symbols (metals, energy, indices, stocks, crypto) ────────
#
# These carry no exchange packet time of the Indian kind, so the guard
# above could never fire for them until the tick started carrying the
# exchange's own clock as `feed_ts`. Our writer re-stamps `ts` on every
# pass whether or not the price moved, so it can't be the measure.

import time as _time

from app.services.binance_futures_service import BinanceFuturesFeed


def _feed_with(book):
    feed = BinanceFuturesFeed()
    feed._handle_book(book)
    return feed


def _book(symbol, bid, ask, event_ms):
    return {"e": "bookTicker", "s": symbol, "b": str(bid), "a": str(ask), "E": event_ms}


def test_tick_carries_the_exchanges_own_time():
    when_ms = 1790000000000
    tick = _feed_with(_book("XAUUSDT", 4200.0, 4200.1, when_ms)).get_tick("XAUUSD")
    assert tick is not None
    assert tick["feed_ts"] == when_ms / 1000.0


def test_a_frozen_stream_blocks_the_trade():
    """The failure this closes: the stream stops, our loop keeps
    republishing the same price with a fresh `ts`, and the trade goes
    through at a price that is minutes old."""
    stale_ms = int((_time.time() - 90) * 1000)
    tick = _feed_with(_book("XAUUSDT", 4200.0, 4200.1, stale_ms)).get_tick("XAUUSD")
    age = _time.time() - tick["feed_ts"]
    assert age > 30
    msg = stale_feed_block_reason(
        symbol="XAUUSD", price_age_sec=age, threshold_sec=30, feed_warm_age_sec=None
    )
    assert msg is not None and "XAUUSD" in msg


def test_an_unknown_symbol_is_unknown_not_fresh():
    """Nothing to judge must skip the guard, never read as "just now"."""
    feed = _feed_with(_book("XAUUSDT", 4200.0, 4200.1, 1790000000000))
    assert feed.get_tick("NOTLISTED") is None
    assert stale_feed_block_reason(
        symbol="NOTLISTED", price_age_sec=None, threshold_sec=30, feed_warm_age_sec=None
    ) is None
