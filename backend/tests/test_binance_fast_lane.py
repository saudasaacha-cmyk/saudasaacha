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


# ── last traded price ────────────────────────────────────────────────


def test_a_trade_beats_the_mid():
    """XAUUSDT's book sends 84 messages a second and its bid/ask moves
    twice — most messages are size changes at the same price. A screen fed
    on mid looks frozen; Binance's own looks alive because it prints
    trades."""
    f = BinanceFuturesFeed()
    f._handle_book({"e": "bookTicker", "s": "XAUUSDT", "b": "4200.00", "a": "4200.10", "E": 1})
    assert f.get_tick("XAUUSD")["ltp"] == 4200.05  # mid, until a trade lands
    f._handle_book({"e": "aggTrade", "s": "XAUUSDT", "p": "4200.07", "E": 2})
    assert f.get_tick("XAUUSD")["ltp"] == 4200.07
    # A later book update must not drag the price back to the mid.
    f._handle_book({"e": "bookTicker", "s": "XAUUSDT", "b": "4200.00", "a": "4200.10", "E": 3})
    assert f.get_tick("XAUUSD")["ltp"] == 4200.07


def test_an_unwatched_symbol_still_has_a_price():
    """No fast lane means no trades — the mid has to stand in, or 500
    instruments would show nothing until somebody opened them."""
    f = BinanceFuturesFeed()
    f._handle_book({"e": "bookTicker", "s": "LLYUSDT", "b": "1000.0", "a": "1001.0", "E": 1})
    assert f.get_tick("LLY")["ltp"] == 1000.5


def test_a_garbage_trade_is_ignored():
    f = BinanceFuturesFeed()
    f._handle_book({"e": "aggTrade", "s": "XAUUSDT", "p": "4200.00", "E": 1})
    f._handle_book({"e": "aggTrade", "s": "XAUUSDT", "p": "1.00", "E": 2})
    assert f.get_tick("XAUUSD")["ltp"] == 4200.00
