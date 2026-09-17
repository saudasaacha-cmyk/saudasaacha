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
