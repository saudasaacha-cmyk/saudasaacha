"""Admin market-status read-out: what the trading paths currently believe.

Every value here is produced by calling the SAME helpers the risk enforcer,
the pending-order poller and the order validator call — never by re-deriving
a schedule locally. That is the only thing that makes the screen worth having:
if it and the platform disagree, the screen is wrong by construction, so it
can never reassure anybody about a gate that is actually mis-set.

It exists because the 2026-11-02 MCX drift — a close-time literal left at
23:40 against a 23:55 session, which shut order entry at 23:30 and stopped
the risk enforcer firing at 23:40, every evening, silently — would have been
one glance here.

Read-only. Nothing in this module writes.
"""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.core.dependencies import CurrentAdmin
from app.core.redis_client import get_redis
from app.models._base import Exchange
from app.models.holiday import TradingHoliday
from app.schemas.common import APIResponse
from app.services.binance_service import binance
from app.services.infoway_service import infoway
from app.services.zerodha_service import zerodha
from app.utils.time_utils import (
    is_after_close,
    is_before_open,
    is_weekend,
    is_within_open_grace,
    market_close_time_for_segment,
    market_open_time_for_segment,
    mcx_session_end,
    now_ist,
    parse_hhmm,
)

router = APIRouter(prefix="/market", tags=["admin-market"])
logger = logging.getLogger(__name__)

# The grace window the poller and the enforcer both hold at the open bell, so
# a stale overnight tick can't book a phantom fill. Mirrors
# matching_engine._OPEN_SETTLE_BUFFER_SEC / risk_enforcer._OPEN_GRACE_SEC.
_OPEN_GRACE_SEC = 60

# One representative segment per group — whatever string the real `Position`
# documents carry, so the helpers take the same branch they take in production.
_GROUPS: list[dict[str, Any]] = [
    {"group": "NSE / BSE equity", "probe": "NSE_EQ", "exchange": Exchange.NSE},
    {"group": "NFO / BFO F&O", "probe": "NFO_FUT", "exchange": Exchange.NSE},
    {"group": "MCX commodities", "probe": "MCX_FUT", "exchange": Exchange.MCX},
    {"group": "Forex (CDS)", "probe": "CDS_FUTURE", "exchange": None},
    {"group": "Crypto", "probe": "CRYPTO_SPOT", "exchange": None},
]


def _hhmm(t: time | None) -> str | None:
    return t.strftime("%H:%M") if t else None


def _session_state(probe: str, now, ctx: dict[str, Any]) -> tuple[str, str | None]:
    """(state, note) for one group, in the ORDER the production gates apply —
    so the label names the reason an order would actually be refused, not a
    prettier one.

    A table rather than an if-chain, because the ORDER is the rule: weekend
    before holiday before pre-open before closed. Conditions are evaluated
    eagerly, which is harmless — every one of them is a pure, cheap predicate,
    and the 24×7 segments return False from all of them.
    """
    hol = ctx["holiday"]
    gates = (
        (ctx["always_on"], "OPEN", "24×7 / 24×5 — no daily session"),
        (ctx["weekend"], "WEEKEND", "Indian exchanges closed"),
        (
            hol is not None and bool(getattr(hol, "is_full_day", False)),
            "HOLIDAY",
            getattr(hol, "description", "") or "exchange holiday",
        ),
        (is_before_open(probe, now), "PRE_OPEN", f"opens {_hhmm(ctx['open_t'])}"),
        (is_after_close(probe, now), "CLOSED", f"gate closed {_hhmm(ctx['gate_t'])}"),
        (
            is_within_open_grace(probe, _OPEN_GRACE_SEC, now),
            "SETTLING",
            "first minute after the bell — parked fills held",
        ),
    )
    for hit, state, note in gates:
        if hit:
            return state, note
    return "OPEN", None


def _entry_close(probe: str, now, always_on: bool):
    """(order-entry close, where it came from).

    For NSE/BSE the order-entry close (15:30, env) and the rollover / risk gate
    (16:00) are deliberately DIFFERENT numbers; for MCX they are the same. The
    screen shows both columns, because a single "close" is exactly what let the
    two drift apart unnoticed.
    """
    if "MCX" in probe:
        return mcx_session_end(now), "auto — US daylight saving"
    if always_on:
        return None, "always on"
    try:
        return parse_hhmm(settings.MARKET_CLOSE_TIME), "env MARKET_CLOSE_TIME"
    except Exception:  # noqa: BLE001
        return None, "env MARKET_CLOSE_TIME (unparseable)"


async def _feeds() -> list[dict[str, Any]]:
    """Connection state per upstream price source. Every call here reads cached
    / Redis state — none of them reach out to an exchange, so the screen can
    poll without adding load to a live feed."""
    out: list[dict[str, Any]] = []
    try:
        z = await zerodha.get_status()
        out.append(
            {
                "name": "Zerodha (NSE / BSE / MCX)",
                "configured": bool(z.get("isConfigured")),
                "connected": bool(z.get("isConnected")),
                "subscribed": z.get("subscribedCount"),
                "sockets": z.get("wsConnections"),
                "last_error": z.get("wsLastError") or None,
            }
        )
    except Exception:  # noqa: BLE001 - a dead feed must still render the page
        logger.exception("market_status_zerodha_failed")
        out.append({"name": "Zerodha (NSE / BSE / MCX)", "error": "unavailable"})

    for label, svc in (
        ("Infoway (forex / metals)", infoway),
        ("Binance (crypto)", binance),
    ):
        try:
            st = svc.status() or {}
            out.append(
                {
                    "name": label,
                    "configured": st.get("configured", True),
                    "connected": bool(st.get("connected")),
                    "subscribed": st.get("subscribed_count") or st.get("subscribed"),
                }
            )
        except Exception:  # noqa: BLE001
            out.append({"name": label, "error": "unavailable"})
    return out


async def _leaders() -> list[dict[str, Any]]:
    """Which leader locks are currently held, by TTL.

    The hot loops run on ONE worker — whichever holds `leader:feed` — so an
    admin request landing on any other worker cannot see them locally. The
    lock TTL is the only cross-worker truth available, which is why this
    reports locks rather than task objects: a lock with no TTL means no worker
    is driving that loop, and for `leader:feed` that means no ticks, no parked
    fills and no stop-outs anywhere on the platform.
    """
    watched = [
        ("leader:feed", "Price ticks + pending-order poller + risk enforcer"),
        ("leader:intraday_to_carry", "EOD MIS→NRML rollover / square-off"),
        ("leader:expiry_cleanup", "Expired-instrument cleanup"),
        ("leader:pnl_sharing_scheduler", "P&L-sharing auto-settlement"),
        ("leader:weekly_settlement", "Weekly mark-to-market settlement"),
    ]
    try:
        r = await get_redis()
    except Exception:  # noqa: BLE001
        logger.exception("market_status_leaders_failed")
        # "I could not tell" and "nothing is holding these" demand opposite
        # reactions, and an empty list reads as the second. Say which it is.
        return [
            {"key": k, "what": w, "held": None, "error": "Redis unreachable"}
            for k, w in watched
        ]

    out: list[dict[str, Any]] = []
    for key, what in watched:
        try:
            ttl = await r.ttl(key)
        except Exception:  # noqa: BLE001
            out.append({"key": key, "what": what, "held": None, "error": "lookup failed"})
            continue
        out.append(
            {
                "key": key,
                "what": what,
                "held": bool(ttl and ttl > 0),
                "ttl_sec": ttl if ttl and ttl > 0 else None,
            }
        )
    return out


@router.get("/status", response_model=APIResponse[dict])
async def market_status(admin: CurrentAdmin):
    """Live session state per segment group, plus feed and leader health."""
    now = now_ist()
    weekend = is_weekend(now.date())

    # One holiday lookup per exchange rather than per group — NSE_EQ and
    # NFO_FUT share an exchange and would otherwise query twice.
    holidays: dict[Any, Any] = {}
    for exch in {g["exchange"] for g in _GROUPS if g["exchange"]}:
        try:
            holidays[exch] = await TradingHoliday.find_one(
                TradingHoliday.holiday_date == now.date(),
                TradingHoliday.exchange == exch,
            )
        except Exception:  # noqa: BLE001
            holidays[exch] = None

    segments: list[dict[str, Any]] = []
    for g in _GROUPS:
        probe = g["probe"]
        open_t = market_open_time_for_segment(probe)
        gate_t = market_close_time_for_segment(probe, now)
        always_on = open_t is None and gate_t is None
        hol = holidays.get(g["exchange"])

        state, why = _session_state(
            probe,
            now,
            {
                "holiday": hol,
                "weekend": weekend,
                "always_on": always_on,
                "open_t": open_t,
                "gate_t": gate_t,
            },
        )
        entry_close, source = _entry_close(probe, now, always_on)

        segments.append(
            {
                "group": g["group"],
                "probe_segment": probe,
                "state": state,
                "note": why,
                "opens": _hhmm(open_t),
                "order_entry_closes": _hhmm(entry_close),
                "risk_gate_closes": _hhmm(gate_t),
                "close_source": source,
                "holiday": (
                    None
                    if hol is None
                    else {
                        "description": getattr(hol, "description", "") or None,
                        "full_day": bool(getattr(hol, "is_full_day", False)),
                        "open_time": getattr(hol, "open_time", None),
                        "close_time": getattr(hol, "close_time", None),
                    }
                ),
            }
        )

    return APIResponse(
        data={
            "now_ist": now.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": now.strftime("%a"),
            "is_weekend": weekend,
            "segments": segments,
            "feeds": await _feeds(),
            "leaders": await _leaders(),
        }
    )
