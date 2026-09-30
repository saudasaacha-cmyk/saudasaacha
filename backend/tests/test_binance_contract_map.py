"""Which Binance contract feeds which instrument.

One function answers this for both the feed and the catalogue sync. A
second copy of these rules is how you seed a duplicate instrument for a
symbol that was already covered, so it gets a test rather than a comment.

    pytest -q backend/tests/test_binance_contract_map.py
"""

from __future__ import annotations

import pytest

from app.services.binance_catalogue_service import segment_for
from app.services.binance_futures_service import contract_for

KNOWN = {
    "XAUUSDT", "XAGUSDT", "XPTUSDT", "XPDUSDT", "CLUSDT", "BZUSDT",
    "NATGASUSDT", "COPPERUSDT", "BTCUSDT", "ETHUSDT", "POLUSDT",
    "AAPLUSDT", "QQQUSDT", "LLYUSDT",
}


@pytest.mark.parametrize(
    ("platform", "contract"),
    [
        # Renames — nothing about "USOIL" suggests "CL".
        ("USOIL", "CLUSDT"),
        ("UKOIL", "BZUSDT"),
        ("XAUUSD", "XAUUSDT"),
        ("NATGAS", "NATGASUSDT"),
        # The USD→USDT swap our crypto instruments already rely on.
        ("BTCUSD", "BTCUSDT"),
        ("POLUSD", "POLUSDT"),
        # Plain quote suffix.
        ("AAPL", "AAPLUSDT"),
        ("LLY", "LLYUSDT"),
        # The contract name itself.
        ("QQQUSDT", "QQQUSDT"),
    ],
)
def test_resolution(platform, contract):
    assert contract_for(platform, KNOWN) == contract


def test_an_unlisted_symbol_resolves_to_nothing():
    """Must be None, not a guess — a wrong guess prices one instrument off
    another's contract."""
    assert contract_for("NIFTY", KNOWN) is None
    assert contract_for("", KNOWN) is None
    assert contract_for("EURUSD", KNOWN) is None


@pytest.mark.parametrize(
    ("meta", "segment"),
    [
        ({"baseAsset": "XAU", "underlyingType": "COMMODITY"}, "COMMODITIES"),
        ({"baseAsset": "CL", "underlyingType": "COMMODITY"}, "COMMODITIES"),
        ({"baseAsset": "LLY", "underlyingType": "EQUITY"}, "STOCKS"),
        ({"baseAsset": "TENCENT", "underlyingType": "HK_EQUITY"}, "STOCKS"),
        ({"baseAsset": "SAMSUNG", "underlyingType": "KR_EQUITY"}, "STOCKS"),
        ({"baseAsset": "OPENAI", "underlyingType": "PREMARKET"}, "STOCKS"),
        ({"baseAsset": "BTC", "underlyingType": "COIN"}, "CRYPTO_SPOT"),
        # Binance types the crypto indices as INDEX; they are not equity
        # indices and must not land in the Indices tab.
        ({"baseAsset": "BTCDOM", "underlyingType": "INDEX"}, "CRYPTO_SPOT"),
        # Binance files these as equities because they are ETF shares.
        ({"baseAsset": "QQQ", "underlyingType": "EQUITY"}, "INDICES"),
        ({"baseAsset": "SPY", "underlyingType": "EQUITY"}, "INDICES"),
        # Forex is retired, so its one pair is not listed at all.
        ({"baseAsset": "USDBRL", "underlyingType": "FX"}, None),
    ],
)
def test_segment_mapping(meta, segment):
    assert segment_for(meta) == segment
