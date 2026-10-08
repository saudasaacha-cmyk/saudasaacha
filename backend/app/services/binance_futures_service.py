"""Binance USDT-M futures feed — the whole exchange on one socket.

This replaces MetaAPI as the source for metals, energy, indices, single
stocks and crypto. What makes it practical where MetaAPI wasn't:

* **One subscription covers everything.** `!bookTicker` streams best bid /
  ask for every contract Binance lists — measured: 744 symbols, ~2,000
  updates in 20 s. There is no per-symbol subscribe, so adding the 700th
  instrument costs nothing. MetaAPI capped us at 100 symbols and made us
  ask for each one.

* **The prices are real derivatives, not tokens.** XAUUSDT is a gold
  perpetual quoting a 1-cent spread against $1.8bn of daily volume, and
  the perp sits ~0.05% off its index. (The PAXG *token* on Binance spot
  runs ~0.27% off spot — that's what an earlier survey of the spot market
  found, and why it looked like only gold was available.)

THREE streams, because the all-market one is sampled:

  WS `!bookTicker`        → every contract, but MEASURED at 0.20 updates/s
                            per symbol. Coverage, not speed: it means a
                            price exists the instant an instrument is
                            listed, with nobody having asked for it.
  WS `<symbol>@bookTicker`→ the same book for ONE contract at 64.8
                            updates/s — 324× the all-market rate. Held for
                            the symbols people are actually watching.
  WS `<symbol>@aggTrade`  → the LAST TRADED price for those same symbols.
                            Measured: XAUUSDT's book sends 84 messages a
                            second but its bid/ask only MOVES twice a
                            second — most messages are size changes at the
                            same price. Binance's own screen looks alive
                            because it prints trades, so we take the trade
                            price as the last price and leave the book to
                            bid/ask.
  REST `/ticker/24hr`     → open / high / low / change, every 10 s, all
                            symbols.

The fast lane is why prices move tick-by-tick instead of drifting once
every few seconds, and why it is bounded: Binance allows 1024 streams on
a connection, and a viewer only ever has a screenful in front of them.

`!ticker@arr` would have given the stats over the socket too, but it never
delivers a frame on this endpoint — subscribing is acknowledged and then
nothing arrives, so the REST poll stands in for it.

NOTE these are PERPETUAL futures: funding settles every 8 h and the
contract carries a small basis to spot. It's tight (measured 0.05% on
gold) but it is not the spot price.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any

import httpx
import websockets

logger = logging.getLogger(__name__)

_WS_URL = "wss://fstream.binance.com/ws"
_REST_BASE = "https://fapi.binance.com"
_STALE_RX_TIMEOUT_SEC = 30       # silent socket → force reconnect (half-open heal)
_RECONNECT_CAP_SEC = 60
_STABLE_CONNECTION_SEC = 30
_STATS_INTERVAL_SEC = 10.0
# Fast lane. Binance caps a connection at 1024 streams and 200 params per
# SUBSCRIBE; this leaves room for the all-market stream and for growth.
# Two streams per symbol (book + trades), so 300 contracts is 600 streams.
_HOT_CAP = 300
# Not asked for in this long → back to the all-market rate. A watchlist the
# user still has open is re-requested well inside the window.
_HOT_TTL_SEC = 900.0
_FAST_LANE_INTERVAL_SEC = 5.0
# How long a trade keeps ownership of the last price before the mid of the
# book takes over again.
_TRADE_LEAD_SEC = 3.0
_SUB_CHUNK = 150
# One lone print this far from the last one is garbage, not a move. Same
# guard the Zerodha / Infoway / spot-Binance feeds carry.
_MAX_TICK_SPIKE_PCT = 0.5

# Platform symbol → Binance contract, where the two names differ. Everything
# else resolves by rule in `_binance_symbol` (exact, +T, +USDT), so this map
# only holds the genuine renames.
_ALIASES: dict[str, str] = {
    "XAUUSD": "XAUUSDT",
    "XAGUSD": "XAGUSDT",
    "XPTUSD": "XPTUSDT",
    "XPDUSD": "XPDUSDT",
    "USOIL": "CLUSDT",      # WTI
    "UKOIL": "BZUSDT",      # Brent
    "NATGAS": "NATGASUSDT",
    "COPPER": "COPPERUSDT",
}


def contract_for(sym: str, known: set[str] | Any) -> str | None:
    """Platform symbol → the Binance contract that carries its price.

    Tried most-specific first: the contract name itself (AAPLUSDT), an
    explicit rename (USOIL → CLUSDT), the USD→USDT swap our crypto
    instruments already rely on (BTCUSD → BTCUSDT), then the plain quote
    suffix (AAPL → AAPLUSDT).

    Shared with the catalogue sync so "which contract feeds this
    instrument" has exactly one answer — a second copy of these rules is
    how you end up seeding a duplicate instrument for a symbol that was
    already covered.
    """
    s = (sym or "").upper()
    if not s:
        return None
    if s in known:
        return s
    alias = _ALIASES.get(s)
    if alias and alias in known:
        return alias
    for cand in (s + "T", s + "USDT"):
        if cand in known:
            return cand
    return None


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


class BinanceFuturesFeed:
    """Singleton feed. Runs in the leader process, like every other feed."""

    def __init__(self) -> None:
        self._ticks: dict[str, dict[str, Any]] = {}
        self._connected = False
        self._last_rx = 0.0
        self._stop = False
        self._task: asyncio.Task[Any] | None = None
        self._stats_task: asyncio.Task[Any] | None = None
        self._fast_task: asyncio.Task[Any] | None = None
        self._symbol_count = 0
        self._ws: Any = None
        # contract → when it was last asked for (monotonic)
        self._hot: dict[str, float] = {}
        # contracts currently carrying a per-symbol stream
        self._fast: set[str] = set()

    # ── public accessors ──────────────────────────────────────────────
    def is_enabled(self) -> bool:
        from app.core.config import settings

        return bool(getattr(settings, "BINANCE_FUTURES_FEED", True))

    @property
    def is_connected(self) -> bool:
        return self._connected

    def contract_name(self, symbol: str | None) -> str | None:
        """The contract whose price this symbol is quoted from, or None.

        The same resolution `get_tick` uses, exposed so the CHART can ask
        for candles from the very contract the quote comes from. They used
        to disagree: candles were pulled from Binance SPOT while the quote
        came from here, so BTC's chart sat ~0.05% off its own price line,
        and anything with no spot pair at all — XAUUSD, USOIL — fell
        through to a Yahoo symbol for a different market entirely.
        """
        if not symbol:
            return None
        return contract_for(symbol, self._ticks)

    def get_tick(self, symbol: str | None) -> dict[str, Any] | None:
        if not symbol:
            return None
        key = contract_for(symbol, self._ticks)
        if key is None:
            return None
        t = self._ticks.get(key)
        if not t or _f(t.get("ltp")) <= 0:
            return None
        return t

    def status(self) -> dict[str, Any]:
        now = time.monotonic()
        return {
            "enabled": self.is_enabled(),
            "connected": self._connected,
            "symbols": self._symbol_count,
            "fast_lane": len(self._fast),
            "tick_count": len(self._ticks),
            "last_rx_age_sec": round(now - self._last_rx, 1) if self._last_rx else None,
        }

    def mark_hot(self, symbols: Any) -> int:
        """Somebody is looking at these — put them on the fast lane.

        Called from the leader's feed-subscribe path, so a watchlist row, an
        open position and the instrument panel's visible rows all land here.
        Cheap and idempotent: it only stamps a time; the reconcile below
        does the talking to Binance.
        """
        now = time.monotonic()
        n = 0
        for sym in symbols or ():
            contract = contract_for(str(sym), self._ticks)
            if contract:
                self._hot[contract] = now
                n += 1
        return n

    def _wanted_fast(self) -> set[str]:
        """The contracts that should hold a per-symbol stream: most recently
        asked for first, anything stale dropped, capped."""
        now = time.monotonic()
        live = [(t, c) for c, t in self._hot.items() if now - t <= _HOT_TTL_SEC]
        live.sort(reverse=True)
        return {c for _t, c in live[:_HOT_CAP]}

    async def _fast_lane_loop(self) -> None:
        """Keep the per-symbol subscriptions matching what's being watched."""
        while not self._stop:
            await asyncio.sleep(_FAST_LANE_INTERVAL_SEC)
            ws = self._ws
            if ws is None or not self._connected:
                self._fast.clear()
                continue
            try:
                want = self._wanted_fast()
                add = sorted(want - self._fast)
                drop = sorted(self._fast - want)
                for method, syms in (("SUBSCRIBE", add), ("UNSUBSCRIBE", drop)):
                    for i in range(0, len(syms), _SUB_CHUNK):
                        chunk = syms[i : i + _SUB_CHUNK]
                        await ws.send(
                            json.dumps(
                                {
                                    "method": method,
                                    "params": [
                                        p
                                        for c in chunk
                                        for p in (
                                            f"{c.lower()}@bookTicker",
                                            f"{c.lower()}@aggTrade",
                                        )
                                    ],
                                    "id": int(time.time() * 1000) % 1_000_000,
                                }
                            )
                        )
                        # Binance drops a connection that sends more than ~10
                        # messages a second.
                        await asyncio.sleep(0.3)
                if add or drop:
                    self._fast = want
                    logger.info(
                        "binance_fast_lane added=%d dropped=%d total=%d",
                        len(add),
                        len(drop),
                        len(self._fast),
                    )
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — the all-market stream still feeds
                logger.warning("binance_fast_lane_failed", exc_info=True)

    # ── lifecycle ─────────────────────────────────────────────────────
    async def start(self) -> None:
        if not self.is_enabled():
            logger.info("binance_futures_skipped: BINANCE_FUTURES_FEED off")
            return
        self._stop = False
        self._task = asyncio.create_task(self._run_loop(), name="binance_futures_feed")
        self._stats_task = asyncio.create_task(
            self._stats_loop(), name="binance_futures_stats"
        )
        self._fast_task = asyncio.create_task(
            self._fast_lane_loop(), name="binance_futures_fast_lane"
        )
        logger.info("binance_futures_feed_started")

    async def stop(self) -> None:
        self._stop = True
        self._connected = False
        for t in (self._task, self._stats_task, self._fast_task):
            if t is not None:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        self._task = self._stats_task = self._fast_task = None

    async def _run_loop(self) -> None:
        backoff = 1
        while not self._stop:
            started = time.monotonic()
            try:
                await self._connect_once()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.warning("binance_futures_ws_error: %s", e)
            finally:
                self._connected = False
            if self._stop:
                break
            if time.monotonic() - started >= _STABLE_CONNECTION_SEC:
                backoff = 1
            ceiling = min(backoff, _RECONNECT_CAP_SEC)
            await asyncio.sleep(ceiling / 2 + random.uniform(0, ceiling / 2))
            backoff = min(backoff * 2, _RECONNECT_CAP_SEC)

    async def _connect_once(self) -> None:
        # The documented `/stream?streams=!bookTicker` form acknowledges the
        # connection and then never sends a frame; the plain `/ws` endpoint
        # with an explicit SUBSCRIBE does work. Verified against production
        # before this was written.
        async with websockets.connect(
            _WS_URL,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            max_size=2**21,
        ) as ws:
            await ws.send(
                json.dumps({"method": "SUBSCRIBE", "params": ["!bookTicker"], "id": 1})
            )
            self._ws = ws
            # A reconnect starts with no per-symbol streams; the fast-lane
            # reconcile puts back whatever is still being watched within a
            # few seconds.
            self._fast.clear()
            self._connected = True
            self._last_rx = time.monotonic()
            logger.info("binance_futures_ws_connected")
            wd = asyncio.create_task(self._watchdog(ws), name="binance_futures_watchdog")
            try:
                async for raw in ws:
                    self._last_rx = time.monotonic()
                    if self._stop:
                        break
                    try:
                        msg = json.loads(raw if isinstance(raw, str) else raw.decode())
                    except Exception:
                        continue
                    self._handle_book(msg)
            finally:
                self._ws = None
                wd.cancel()
                try:
                    await wd
                except (asyncio.CancelledError, Exception):
                    pass

    async def _watchdog(self, ws: Any) -> None:
        while True:
            await asyncio.sleep(10)
            if time.monotonic() - self._last_rx > _STALE_RX_TIMEOUT_SEC:
                logger.warning("binance_futures_stale_rx_forcing_reconnect")
                try:
                    await ws.close()
                except Exception:
                    pass
                return

    def _handle_book(self, msg: dict[str, Any]) -> None:
        if not isinstance(msg, dict):
            return
        kind = msg.get("e")
        if kind == "aggTrade":
            self._handle_trade(msg)
            return
        if kind != "bookTicker":
            return  # the SUBSCRIBE ack has no "e"
        sym = str(msg.get("s") or "").upper()
        if not sym:
            return
        bid, ask = _f(msg.get("b")), _f(msg.get("a"))
        if bid <= 0 or ask <= 0:
            return
        mid = (bid + ask) / 2.0
        t = self._ticks.setdefault(sym, {})
        prev = _f(t.get("ltp"))
        if prev > 0 and abs(mid - prev) / prev > _MAX_TICK_SPIKE_PCT:
            logger.warning(
                "binance_futures_bad_tick_skipped sym=%s prev=%s new=%s", sym, prev, mid
            )
            return
        t["bid"], t["ask"] = bid, ask
        # Whichever is more recent wins. A busy contract prints constantly
        # and the trade price leads; a quiet one (gold at 09:00 UTC) can go
        # ten seconds without a print, and pinning the last price to a stale
        # trade froze it — worse than the mid it replaced. So the mid takes
        # over once the trade tape goes quiet.
        if time.time() - _f(t.get("last_trade_ts")) > _TRADE_LEAD_SEC:
            t["ltp"] = mid
        if t.get("open"):
            t["change"] = mid - _f(t["open"])
            t["change_pct"] = t["change"] / _f(t["open"]) * 100.0
        # Binance's OWN event time, so the stale-price guard measures the
        # exchange's clock rather than ours — our tick loop re-stamps its
        # `ts` every pass whether or not the price moved.
        ev = _f(msg.get("E"))
        t["feed_ts"] = ev / 1000.0 if ev > 0 else time.time()
        t["ts"] = time.time()

    def _handle_trade(self, msg: dict[str, Any]) -> None:
        """Last traded price — what makes a quiet book still look alive."""
        sym = str(msg.get("s") or "").upper()
        price = _f(msg.get("p"))
        if not sym or price <= 0:
            return
        t = self._ticks.setdefault(sym, {})
        prev = _f(t.get("ltp"))
        if prev > 0 and abs(price - prev) / prev > _MAX_TICK_SPIKE_PCT:
            logger.warning(
                "binance_futures_bad_trade_skipped sym=%s prev=%s new=%s", sym, prev, price
            )
            return
        t["ltp"] = price
        t["last_trade_ts"] = time.time()
        if t.get("open"):
            t["change"] = price - _f(t["open"])
            t["change_pct"] = t["change"] / _f(t["open"]) * 100.0
        ev = _f(msg.get("E"))
        t["feed_ts"] = ev / 1000.0 if ev > 0 else time.time()
        t["ts"] = time.time()

    async def _stats_loop(self) -> None:
        """24 h open / high / low / volume for every contract, every 10 s.

        One call returns all ~790 symbols (weight 40 against a 2,400/min
        budget), so this is far cheaper than per-symbol streams and the
        numbers it carries move slowly enough that 10 s is plenty.
        """
        while not self._stop:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    r = await client.get(f"{_REST_BASE}/fapi/v1/ticker/24hr")
                    r.raise_for_status()
                    rows = r.json()
                if isinstance(rows, list):
                    self._symbol_count = len(rows)
                    for row in rows:
                        sym = str(row.get("symbol") or "").upper()
                        if not sym:
                            continue
                        t = self._ticks.setdefault(sym, {})
                        t["open"] = _f(row.get("openPrice"))
                        t["high"] = _f(row.get("highPrice"))
                        t["low"] = _f(row.get("lowPrice"))
                        t["volume"] = _f(row.get("volume"))
                        t["change"] = _f(row.get("priceChange"))
                        t["change_pct"] = _f(row.get("priceChangePercent"))
                        t["close_24h"] = _f(row.get("openPrice"))
                        # A contract nobody is quoting yet still needs a price
                        # for the catalogue; the socket overwrites it the
                        # moment a real book update lands.
                        if _f(t.get("ltp")) <= 0:
                            last = _f(row.get("lastPrice"))
                            if last > 0:
                                t["ltp"] = t["bid"] = t["ask"] = last
                                t["ts"] = time.time()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.warning("binance_futures_stats_failed", exc_info=True)
            await asyncio.sleep(_STATS_INTERVAL_SEC)


binance_futures = BinanceFuturesFeed()
