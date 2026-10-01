"""Forex is retired — no segment row, no mapping, nothing left pointing at it.

The only feed that ever carried forex was MetaAPI, which is gone, and Binance
lists a single FX pair. What remained was a segment the admin could configure
and nobody could get a price for.

    pytest -q backend/tests/test_forex_retired.py
"""

from __future__ import annotations

from app.services.netting_service import (
    INTRADAY_ONLY_ADMIN_ROWS,
    RETIRED_SEGMENT_NAMES,
    SEGMENT_DEFAULTS,
    _SEGMENT_NAME_MAP,
    resolve_admin_row,
)


def test_forex_is_not_a_segment_the_admin_can_configure():
    assert "FOREX" not in {d["name"] for d in SEGMENT_DEFAULTS}
    assert "FOREX" not in INTRADAY_ONLY_ADMIN_ROWS


def test_forex_is_retired_so_boot_cleans_its_rows():
    """`cleanup_retired_segments` walks this tuple on every start — that is
    what drops the NettingSegment row and the overrides hanging off it."""
    assert "FOREX" in RETIRED_SEGMENT_NAMES


def test_nothing_resolves_to_the_forex_row_any_more():
    """Including the NSE currency-derivative segments, which used to borrow
    the forex row for their settings."""
    assert "FOREX" not in set(_SEGMENT_NAME_MAP.values())
    for seg in ("CDS_FUTURE", "CDS_OPTION_BUY", "CDS_OPTION_SELL"):
        assert resolve_admin_row(seg, None) != "FOREX"
    # An unmapped segment still owns itself, so a hypothetical row carrying
    # segment="FOREX" resolves to the name "FOREX". That is only a label:
    # there is no such row in SEGMENT_DEFAULTS to carry settings, and the
    # boot sweep deletes any instrument that holds that segment.
    assert resolve_admin_row("FOREX", None) == "FOREX"


def test_the_other_international_rows_are_untouched():
    """Forex went out alongside STOCKS / INDICES / COMMODITIES / CRYPTO —
    those are live and must keep resolving."""
    names = {d["name"] for d in SEGMENT_DEFAULTS}
    for row in ("STOCKS", "INDICES", "COMMODITIES", "CRYPTO"):
        assert row in names
    assert resolve_admin_row("CRYPTO_SPOT", "BTC") == "CRYPTO"
    assert resolve_admin_row("COMMODITIES", "XAUUSD") == "COMMODITIES"
