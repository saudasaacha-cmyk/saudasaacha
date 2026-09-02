"""MetaAPI (MetaTrader 4/5) feed for FOREX / METALS / INDICES / COMMODITIES.

Streams real-time bid/ask from a connected MT4/MT5 account via metaapi.cloud.
Wired in as the price source for those segments (in place of Infoway) when
``METAAPI_FEED=true``. Crypto stays on Binance; Infoway remains the automatic
FALLBACK if MetaAPI has no tick for a symbol, so nothing breaks during rollout.

Same in-memory-cache shape as ``infoway_service`` / ``binance_service``:
``get_tick(symbol)`` returns ``{ltp, bid, ask, change, change_pct, volume, open,
high, low, close_24h}`` so ``market_data_service._infoway_overlay`` merges it
identically. LTP = mid (bid+ask)/2. Rolling intraday OHLC + session change are
synthesised from the streamed quotes (MT quotes carry no 24h stats), exactly
like the Infoway path.

The streaming SDK keeps ``connection.terminal_state`` fresh in real time; the
0.1 s market tick_loop samples ``get_tick`` off it, so movement is smooth/fast
(well under the requested 0.25 s cadence) without any extra loop here.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Reject a lone tick that jumps more than this fraction vs the last price —
# mirrors infoway_service / binance_service spike guards.
_MAX_TICK_SPIKE_PCT = 0.5


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _silence_sdk_loggers() -> None:
    """The metaapi-cloud-sdk (socket.io / engine.io transport) logs EVERY
    websocket packet at INFO — including the full symbol-specifications dump
    (thousands of instruments). Left alone it floods journalctl + burns disk.
    Pin those transport loggers to WARNING so only real problems surface."""
    for name in (
        "engineio",
        "engineio.client",
        "socketio",
        "socketio.client",
        "metaapi",
        "aiohttp.access",
    ):
        try:
            logging.getLogger(name).setLevel(logging.WARNING)
        except Exception:
            pass


class MetaApiFeed:
    """Singleton MT feed. Lives in the running backend process (leader)."""

    def __init__(self) -> None:
        self._api: Any = None
        self._account: Any = None
        self._conn: Any = None
        self._connected = False
        self._symbols: list[str] = []
        # Per-symbol rolling state for OHLC + change synthesis.
        self._state: dict[str, dict[str, float]] = {}
        self._alias: dict[str, str] = {}   # platform symbol -> MT broker symbol
        # Broker symbols this MT account does NOT offer (returned "symbol does
        # not exist"). Memoised so we never re-attempt them — otherwise every
        # WS subscribe of a crypto/forex/stock token the broker lacks (e.g.
        # CRYPTO_BTCUSD, BTCUSDT, FX_EURUSD, NSE_EQ_*) re-fires a doomed
        # subscribe on every tick and floods the (isolated) feed process CPU
        # + journal with metaapi_on_demand_subscribe_failed.
        self._unavailable: set[str] = set()
        # MetaAPI accounts have a HARD per-account cap on concurrent symbol
        # subscriptions (plan-dependent; the current plan = 25). Exceeding it
        # makes the SDK's subscription_manager retry the rejected symbol every
        # ~10s forever with a TooManyRequestsException(429) flood, and the
        # excess symbols get no MetaAPI tick. We therefore cap our own list a
        # touch below the account limit; symbols beyond the cap simply fall
        # back to the Infoway feed (market_data_service._infoway_overlay already
        # does MetaAPI-first-then-Infoway), so nothing freezes.
        self._max_symbols: int = int(getattr(settings, "METAAPI_MAX_SYMBOLS", 24) or 24)
        self._cap_log_ts = 0.0
        self._task: asyncio.Task[Any] | None = None
        self._stop = False
        self._last_rx = 0.0

    # ── public accessors ──────────────────────────────────────────────
    def is_enabled(self) -> bool:
        try:
            has_token = bool(settings.METAAPI_TOKEN.get_secret_value())
        except Exception:
            has_token = False
        return bool(
            getattr(settings, "METAAPI_FEED", False)
            and has_token
            and getattr(settings, "METAAPI_ACCOUNT_ID", "")
        )

    @property
    def is_connected(self) -> bool:
        return self._connected

    def status(self) -> dict[str, Any]:
        now = time.time()
        return {
            "enabled": self.is_enabled(),
            "connected": self._connected,
            "symbols": self._symbols,
            "tick_count": len(self._state),
            "last_rx_age_sec": round(now - self._last_rx, 1) if self._last_rx else None,
        }

    def _mt_symbol(self, sym: str) -> str:
        """Map a platform symbol to the MT broker's symbol (they can differ:
        US30/DJ30, USOIL/WTI, EURUSD/EURUSD.raw). Alias map comes from
        METAAPI_SYMBOL_MAP; default is identity."""
        return self._alias.get(sym, sym)

    def _looks_non_metaapi(self, sym: str) -> bool:
        """Cheap pre-filter for PLATFORM tokens that clearly aren't MT symbols,
        so we never even attempt a subscribe the broker will always reject:
          - namespaced platform tokens carry an underscore (CRYPTO_BTCUSD,
            FX_EURUSD, NSE_EQ_TATAMOTORS) — real MT symbols don't (EURUSD,
            XAUUSD, USOIL, SPX500, AAPL.US).
          - Binance-style crypto pairs end in USDT (BTCUSDT, ETHUSDT).
        MetaAPI only carries forex / metals / energy / indices / US-stocks."""
        s = (sym or "").upper()
        return ("_" in s) or s.endswith("USDT")

    def _note_sub_error(self, broker: str, err: Exception, log_msg: str) -> None:
        """Classify a subscribe failure. A "symbol does not exist" is EXPECTED
        for non-MetaAPI tokens — memoise it (never retry) and log at debug so
        it doesn't flood. Anything else is a real problem → warning."""
        text = str(err).lower()
        if "does not exist" in text or "not found" in text:
            self._unavailable.add(broker)
            logger.debug("%s %s: not offered by broker (memoised)", log_msg, broker)
        else:
            logger.warning("%s %s: %s", log_msg, broker, err)

    def get_tick(self, symbol: str | None) -> dict[str, Any] | None:
        if not symbol or self._conn is None:
            return None
        sym = symbol.upper()
        mt = self._mt_symbol(sym)
        price = None
        try:
            ts = self._conn.terminal_state
            if ts is not None:
                price = ts.price(symbol=mt)
        except Exception:
            price = None
        if not price:
            return None
        bid = _f(price.get("bid"))
        ask = _f(price.get("ask"))
        if bid <= 0 and ask <= 0:
            return None
        ltp = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else (bid or ask)
        if ltp <= 0:
            return None

        st = self._state.get(sym)
        if st is None:
            st = {"open": ltp, "high": ltp, "low": ltp, "last": ltp}
            self._state[sym] = st
        else:
            prev = st.get("last") or ltp
            # Bad-tick spike guard — ignore a lone >50% jump, keep last-known.
            if prev > 0 and abs(ltp - prev) / prev > _MAX_TICK_SPIKE_PCT:
                ltp = prev
                bid = st.get("bid", bid)
                ask = st.get("ask", ask)
            else:
                if ltp > st["high"]:
                    st["high"] = ltp
                if ltp < st["low"]:
                    st["low"] = ltp
        st["last"] = ltp
        st["bid"] = bid
        st["ask"] = ask
        self._last_rx = time.time()
        change = ltp - st["open"]
        return {
            "ltp": ltp,
            "bid": bid,
            "ask": ask,
            "change": change,
            "change_pct": (change / st["open"] * 100.0) if st["open"] else 0.0,
            "volume": 0.0,
            "open": st["open"],
            "high": st["high"],
            "low": st["low"],
            "close_24h": st["open"],  # no true prev-close from MT → session open
            "ts": self._last_rx,
        }

    # ── config ────────────────────────────────────────────────────────
    def _resolve_symbols(self) -> list[str]:
        raw = (getattr(settings, "METAAPI_SYMBOLS", "") or "").strip()
        if not raw:
            # Default: reuse the Infoway forex / metals / energy / indices lists
            # (same standard MT symbol names — EURUSD, XAUUSD, USOIL, SPX500…).
            parts = [
                getattr(settings, "INFOWAY_DEFAULT_FOREX", "") or "",
                getattr(settings, "INFOWAY_DEFAULT_METALS", "") or "",
                getattr(settings, "INFOWAY_DEFAULT_ENERGY", "") or "",
                getattr(settings, "INFOWAY_DEFAULT_INDICES", "") or "",
            ]
            raw = ",".join(p for p in parts if p)
        seen: set[str] = set()
        out: list[str] = []
        for s in (x.strip().upper() for x in raw.split(",")):
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        # Never seed more than the account's subscription cap — the remainder
        # would only trigger 429 retry floods (see `_max_symbols`).
        if len(out) > self._max_symbols:
            logger.warning(
                "metaapi_startup_symbols_capped from=%d to=%d", len(out), self._max_symbols
            )
            out = out[: self._max_symbols]
        return out

    def _resolve_alias(self) -> dict[str, str]:
        raw = (getattr(settings, "METAAPI_SYMBOL_MAP", "") or "").strip()
        out: dict[str, str] = {}
        for pair in raw.split(","):
            if ":" in pair:
                p, m = pair.split(":", 1)
                p = p.strip().upper()
                m = m.strip()
                if p and m:
                    out[p] = m
        return out

    # ── lifecycle ─────────────────────────────────────────────────────
    async def start(self) -> None:
        if not self.is_enabled():
            logger.info("metaapi_feed_skipped: METAAPI_FEED off or token/account missing")
            return
        _silence_sdk_loggers()
        self._symbols = self._resolve_symbols()
        self._alias = self._resolve_alias()
        self._stop = False
        self._task = asyncio.create_task(self._run_loop(), name="metaapi_feed")
        logger.info(
            "metaapi_feed_started symbols=%d aliases=%d", len(self._symbols), len(self._alias)
        )

    async def subscribe(self, symbols: list[str]) -> None:
        """On-demand: ensure `symbols` are streamed by the MT terminal.

        The startup list (`_resolve_symbols`) covers the default forex / metals
        / energy / indices, but a watchlist symbol outside that list would
        never be subscribed upstream → `terminal_state.price` returns None →
        `get_tick` None → frozen 0.0000. Callers pass PLATFORM symbols; we map
        each through the alias to the broker name before subscribing. Newly
        seen symbols are also remembered so a reconnect re-subscribes them.
        Best-effort + idempotent (the SDK no-ops an already-subscribed symbol).
        """
        if not symbols:
            return
        for raw in symbols:
            sym = (raw or "").strip().upper()
            if not sym:
                continue
            broker = self._mt_symbol(sym)
            # Skip tokens the broker doesn't carry (already-known-unavailable or
            # an obviously-non-MetaAPI namespace) so we don't pollute the
            # persistent symbol list or spam doomed subscribes every tick.
            if broker in self._unavailable or self._looks_non_metaapi(sym):
                continue
            if sym not in self._symbols:
                # Respect the account subscription cap — a new symbol beyond it
                # would 429-flood; it falls back to Infoway instead (no freeze).
                if len(self._symbols) >= self._max_symbols:
                    now = time.time()
                    if now - self._cap_log_ts > 60:
                        self._cap_log_ts = now
                        logger.info(
                            "metaapi_subscription_cap_reached max=%d skipping=%s "
                            "(uses Infoway fallback)", self._max_symbols, sym
                        )
                    continue
                self._symbols.append(sym)
            if self._conn is None or not self._connected:
                continue  # will be picked up by the startup subscribe on connect
            try:
                await self._conn.subscribe_to_market_data(broker)
            except Exception as e:  # noqa: BLE001
                self._note_sub_error(broker, e, "metaapi_on_demand_subscribe_failed")

    async def stop(self) -> None:
        self._stop = True
        try:
            if self._conn is not None:
                await self._conn.close()
        except Exception:
            pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _run_loop(self) -> None:
        backoff = 2
        while not self._stop:
            try:
                await self._connect_once()
                backoff = 2
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001
                logger.warning("metaapi_error: %s", e)
            finally:
                self._connected = False
                try:
                    if self._conn is not None:
                        await self._conn.close()
                except Exception:
                    pass
                self._conn = None
            if self._stop:
                break
            await asyncio.sleep(min(backoff, 60))
            backoff = min(backoff * 2, 60)

    async def _connect_once(self) -> None:
        from metaapi_cloud_sdk import MetaApi  # imported lazily so the dep is optional

        token = settings.METAAPI_TOKEN.get_secret_value()
        acc_id = settings.METAAPI_ACCOUNT_ID
        region = (getattr(settings, "METAAPI_REGION", "") or "").strip()

        self._api = MetaApi(token, {"region": region}) if region else MetaApi(token)
        self._account = await self._api.metatrader_account_api.get_account(acc_id)

        # Ensure the account is deployed + connected to the broker before we
        # open the market-data stream. Best-effort — a already-deployed account
        # just no-ops.
        try:
            state = getattr(self._account, "state", None)
            if state and state not in ("DEPLOYED",):
                await self._account.deploy()
            await self._account.wait_connected()
        except Exception as e:
            logger.warning("metaapi_deploy_wait_warning: %s", e)

        self._conn = self._account.get_streaming_connection()
        await self._conn.connect()
        await self._conn.wait_synchronized({"timeoutInSeconds": 60})
        self._connected = True
        self._last_rx = time.monotonic()
        logger.info("metaapi_connected account=%s", acc_id)

        _sub_count = 0
        for s in self._symbols:
            broker = self._mt_symbol(s)
            if broker in self._unavailable or self._looks_non_metaapi(s):
                continue
            try:
                await self._conn.subscribe_to_market_data(broker)
                _sub_count += 1
            except Exception as e:  # noqa: BLE001
                self._note_sub_error(broker, e, "metaapi_subscribe_failed")

        logger.info("metaapi_subscribed symbols=%d", _sub_count)

        # Keep the connection alive; the SDK streams into terminal_state in the
        # background. Bail out (→ reconnect) if it desynchronises.
        while not self._stop:
            await asyncio.sleep(5)
            try:
                if not getattr(self._conn, "synchronized", True):
                    logger.warning("metaapi_desynchronised_forcing_reconnect")
                    return
            except Exception:
                return


metaapi = MetaApiFeed()
