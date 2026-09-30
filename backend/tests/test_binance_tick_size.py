"""The tick Binance publishes is what the chart turns into decimal places.

A row carrying the old 0.05 default drew DOGE (0.08123) on a 2-decimal axis,
so `sync_catalogue` has to refresh `tick_size`, not only set it on insert.
These cover the extraction and the comparison the refresh branch uses — a
string compare there would rewrite every row on every sync, because Binance
pads its ticks with trailing zeros.
"""

from decimal import Decimal

from app.services.binance_catalogue_service import _tick_size


def _meta(tick: str | None):
    filters = [{"filterType": "LOT_SIZE", "stepSize": "1"}]
    if tick is not None:
        filters.append({"filterType": "PRICE_FILTER", "tickSize": tick})
    return {"filters": filters}


def test_tick_comes_from_the_price_filter():
    assert _tick_size(_meta("0.0000100")) == "0.0000100"
    assert _tick_size(_meta("0.10")) == "0.10"


def test_missing_filter_falls_back():
    assert _tick_size(_meta(None)) == "0.01"
    assert _tick_size({}) == "0.01"


def test_padded_tick_equals_the_stored_one():
    # What the refresh branch asks: is the stored tick already right? Binance
    # sends "0.0000100" where Mongo may hold "0.00001" — same tick, so the
    # compare must be by value or the sync writes to all 742 rows forever.
    assert Decimal("0.00001") == Decimal(_tick_size(_meta("0.0000100")))
    assert Decimal("0.05") != Decimal(_tick_size(_meta("0.0000100")))
