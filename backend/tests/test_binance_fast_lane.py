"""Which symbols get a real-time stream.

Binance's all-market book stream is sampled: measured against production,
XAUUSDT arrives 0.20 times a second there and 64.8 times a second on its
own stream. So coverage and speed are two different subscriptions, and the
fast one is rationed — a connection allows 1024 streams and a viewer only
has a screenful open.

    pytest -q backend/tests/test_binance_fast_lane.py
"""

from __future__ import annotations

import time

from app.services import binance_futures_service as bf
from app.services.binance_futures_service import BinanceFuturesFeed


def _feed(contracts):
    f = BinanceFuturesFeed()
    for c in contracts:
        f._ticks[c] = {"ltp": 1.0}
    return f


def test_marking_resolves_platform_symbols_to_contracts():
    f = _feed(["XAUUSDT", "CLUSDT", "AAPLUSDT"])
    assert f.mark_hot(["XAUUSD", "USOIL", "AAPL"]) == 3
    assert f._wanted_fast() == {"XAUUSDT", "CLUSDT", "AAPLUSDT"}


def test_an_unlisted_symbol_is_ignored():
    """NIFTY is Zerodha's; asking Binance for it would just be rejected."""
    f = _feed(["XAUUSDT"])
    assert f.mark_hot(["NIFTY", "XAUUSD"]) == 1
    assert f._wanted_fast() == {"XAUUSDT"}


def test_stale_interest_falls_off():
    f = _feed(["XAUUSDT", "CLUSDT"])
    f.mark_hot(["XAUUSD", "USOIL"])
    f._hot["CLUSDT"] = time.monotonic() - bf._HOT_TTL_SEC - 1
    assert f._wanted_fast() == {"XAUUSDT"}


def test_the_cap_keeps_the_most_recently_asked_for(monkeypatch):
    """Over budget, the screen someone is looking at now wins over the one
    they scrolled past — otherwise the fast lane fills with history."""
    monkeypatch.setattr(bf, "_HOT_CAP", 2)
    f = _feed(["AUSDT", "BUSDT", "CUSDT"])
    now = time.monotonic()
    f._hot = {"AUSDT": now - 30, "BUSDT": now - 20, "CUSDT": now - 10}
    assert f._wanted_fast() == {"BUSDT", "CUSDT"}


def test_nothing_watched_means_no_fast_lane():
    assert _feed(["XAUUSDT"])._wanted_fast() == set()
