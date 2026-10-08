"""The chart and the price must name the SAME Binance contract.

The candles used to come from Binance SPOT while the quote came from the
USDT-M futures feed. BTC's chart then sat ~0.05% off its own price line and
drifted with the basis; worse, most of what we list has no spot pair at all
(XAUUSDT, CLUSDT, the equity perps), so those charts fell through to a Yahoo
symbol for a different instrument entirely — which is what "chart kabhi
kabhi alag dikhta hai" was.

    pytest -q backend/tests/test_chart_matches_feed.py
"""

from __future__ import annotations

from app.api.v1.user.instruments import _fetch_binance_klines
from app.services.binance_futures_service import BinanceFuturesFeed, contract_for

# What the live tick map looks like once the feed has warmed.
KNOWN = {"BTCUSDT", "ETHUSDT", "XAUUSDT", "CLUSDT", "AAPLUSDT", "DOGEUSDT"}


def _feed(known=KNOWN) -> BinanceFuturesFeed:
    f = BinanceFuturesFeed()
    f._ticks = {k: {"ltp": 1.0} for k in known}
    return f


def test_the_chart_asks_the_feed_which_contract_to_draw():
    """One resolver, so the two can't disagree: whatever `contract_for`
    answers for the quote is what the chart is told to fetch."""
    feed = _feed()
    for symbol in ("BTCUSD", "XAUUSD", "USOIL", "AAPL", "DOGEUSDT"):
        assert feed.contract_name(symbol) == contract_for(symbol, KNOWN)


def test_the_instruments_with_no_spot_pair_now_resolve():
    """These are the ones that used to land on Yahoo. XAUUSD and USOIL have
    no Binance SPOT listing at all — only a perpetual."""
    feed = _feed()
    assert feed.contract_name("XAUUSD") == "XAUUSDT"
    assert feed.contract_name("USOIL") == "CLUSDT"
    assert feed.contract_name("AAPL") == "AAPLUSDT"


def test_an_unknown_symbol_resolves_to_nothing():
    """So the caller falls through to Yahoo / Zerodha rather than asking
    Binance for a contract it doesn't list."""
    feed = _feed()
    assert feed.contract_name("NIFTY") is None
    assert feed.contract_name("RELIANCE") is None
    assert feed.contract_name(None) is None
    assert feed.contract_name("") is None


def test_candles_are_pulled_from_the_futures_venue():
    """`fapi` is the futures REST host; `api.binance.com` is spot. The feed
    is futures, so the candles have to be too."""
    import inspect

    src = inspect.getsource(_fetch_binance_klines)
    assert "fapi.binance.com/fapi/v1/klines" in src
    assert "api.binance.com/api/v3" not in src
