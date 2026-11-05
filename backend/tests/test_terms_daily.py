"""Terms acceptance lasts one IST day, not forever.

The operator wants a dated consent: whoever logs in after midnight is asked
again, so there is a record of acceptance for each trading day rather than
one tick from whenever the account was opened.

    pytest -q backend/tests/test_terms_daily.py
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.api.v1.user.support import accepted_today
from app.utils.time_utils import now_ist, now_utc


def test_never_accepted():
    assert not accepted_today(None)


def test_accepted_moments_ago():
    assert accepted_today(now_utc())


def test_yesterday_at_one_minute_to_midnight_does_not_count():
    """23:59 IST is yesterday's consent at 00:01 — that is the whole point
    of the feature, not an edge case to round away."""
    ts = (now_ist() - timedelta(days=1)).replace(hour=23, minute=59)
    assert not accepted_today(ts.astimezone(UTC))


def test_today_at_one_minute_past_midnight_counts():
    ts = now_ist().replace(hour=0, minute=1)
    assert accepted_today(ts.astimezone(UTC))


def test_a_day_old_acceptance_expires():
    assert not accepted_today(now_utc() - timedelta(hours=25))


def test_a_naive_timestamp_is_read_as_utc():
    """Rows written before this existed carry tz-aware UTC, but a naive one
    must not be read as IST and silently count as today."""
    assert accepted_today(datetime.now(UTC).replace(tzinfo=None))
    old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2)
    assert not accepted_today(old)
