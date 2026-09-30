"""Mirror Binance's USDT-M futures listing into the instrument catalogue.

Binance lists ~790 contracts and classifies each one itself
(`underlyingType`), so the segment a user finds an instrument under comes
from the exchange rather than a list we maintain by hand.

    COMMODITY                                   → COMMODITIES
    EQUITY / HK_ / KR_ / CN_EQUITY / PREMARKET  → STOCKS
    COIN and the crypto indices (BTCDOM, ALL)   → CRYPTO_SPOT
    FX                                          → skipped

The one hand-kept list is `_INDEX_ETFS`: Binance types QQQ and SPY as
equities, but somebody looking for "NAS100" expects to find them under
Indices, not filed between MSFT and NVDA.

Instruments already in the catalogue are LEFT ALONE. XAUUSD keeps its
token, its open positions and its trade history, and simply gets its
price from XAUUSDT — `contract_for` decides that, the same function the
feed uses, so the two can't disagree and seed a duplicate.

Only USDT-quoted contracts are taken. The USDC / USD1 duplicates quote the
same asset, and letting both in would put two rows for one instrument in
front of the user.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from bson import Decimal128

from app.models._base import Exchange, InstrumentType
from app.models.instrument import Instrument
from app.services.binance_futures_service import contract_for

logger = logging.getLogger(__name__)

_EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"

# Segments this sync owns. An instrument outside these is none of its
# business — Zerodha's NSE / MCX rows must never be touched.
MANAGED_SEGMENTS = ("COMMODITIES", "STOCKS", "INDICES", "CRYPTO_SPOT", "FOREX")

_EQUITY_TYPES = {"EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "PREMARKET"}

# Binance files these as equities because they are ETF shares. Users look
# for them as indices.
_INDEX_ETFS = {
    "QQQ", "SPY", "IWM", "EWJ", "EWY", "EWT", "EWZ",
    "SMH", "XBI", "XLE", "GDX", "URNM", "KODEX200", "BITO",
}

# Friendlier names than the bare ticker, for the ones whose ticker tells a
# user nothing. Everything else keeps its ticker as the name.
_NICE_NAMES = {
    "QQQ": "Nasdaq 100 ETF (QQQ)",
    "SPY": "S&P 500 ETF (SPY)",
    "IWM": "Russell 2000 ETF (IWM)",
    "EWJ": "Japan ETF (EWJ)",
    "EWY": "South Korea ETF (EWY)",
    "EWT": "Taiwan ETF (EWT)",
    "EWZ": "Brazil ETF (EWZ)",
    "SMH": "Semiconductor ETF (SMH)",
    "XBI": "Biotech ETF (XBI)",
    "XLE": "Energy Sector ETF (XLE)",
    "GDX": "Gold Miners ETF (GDX)",
    "URNM": "Uranium Miners ETF (URNM)",
    "BITO": "Bitcoin Strategy ETF (BITO)",
    "KODEX200": "KOSPI 200 ETF (KODEX 200)",
    "CL": "WTI Crude Oil",
    "BZ": "Brent Crude Oil",
    "NATGAS": "Natural Gas",
    "COPPER": "Copper",
    "XAU": "Gold (XAU)",
    "XAG": "Silver (XAG)",
    "XPT": "Platinum (XPT)",
    "XPD": "Palladium (XPD)",
    "BTCDOM": "Bitcoin Dominance Index",
}


def segment_for(meta: dict[str, Any]) -> str | None:
    """Which platform segment this contract belongs in. None = don't list."""
    base = str(meta.get("baseAsset") or "").upper()
    utype = str(meta.get("underlyingType") or "").upper()
    if utype == "COMMODITY":
        return "COMMODITIES"
    if base in _INDEX_ETFS:
        return "INDICES"
    if utype in _EQUITY_TYPES:
        return "STOCKS"
    if utype == "FX":
        # Retired with MetaAPI: Binance lists exactly one pair (USDBRL) and
        # it can go a minute without a print. A forex segment with one
        # illiquid instrument is worse than none.
        return None
    return "CRYPTO_SPOT"


def _tick_size(meta: dict[str, Any]) -> str:
    for f in meta.get("filters") or []:
        if f.get("filterType") == "PRICE_FILTER" and f.get("tickSize"):
            return str(f["tickSize"])
    return "0.01"


async def fetch_contracts() -> list[dict[str, Any]]:
    """Every USDT-quoted contract Binance is currently trading."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(_EXCHANGE_INFO_URL)
        r.raise_for_status()
        data = r.json()
    return [
        s
        for s in (data.get("symbols") or [])
        if s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT"
    ]


async def sync_catalogue(*, dry_run: bool = False) -> dict[str, Any]:
    """Add every Binance contract the catalogue doesn't already carry.

    Never updates or deletes an existing instrument: its token is what
    positions, orders and watchlists point at.
    """
    contracts = await fetch_contracts()
    by_symbol = {c["symbol"]: c for c in contracts}
    known = set(by_symbol)

    existing = await Instrument.find(
        {"segment": {"$in": list(MANAGED_SEGMENTS)}}
    ).to_list()
    # Which contracts are already represented, resolved exactly the way the
    # feed resolves them.
    covered = {
        c
        for c in (contract_for(i.symbol, known) for i in existing)
        if c is not None
    }
    existing_tokens = {i.token for i in existing}

    created: list[str] = []
    per_segment: dict[str, int] = {}
    skipped_fx = 0

    for sym, meta in by_symbol.items():
        if sym in covered:
            continue
        seg = segment_for(meta)
        if seg is None:
            skipped_fx += 1
            continue
        base = str(meta["baseAsset"]).upper()
        # Token is the contract name: unique by construction, and it says
        # exactly which Binance contract the price comes from.
        token = sym
        if token in existing_tokens:
            continue
        per_segment[seg] = per_segment.get(seg, 0) + 1
        created.append(sym)
        if dry_run:
            continue
        await Instrument(
            token=token,
            symbol=base,
            trading_symbol=sym,
            name=_NICE_NAMES.get(base, base),
            exchange=Exchange.CRYPTO,
            segment=seg,
            instrument_type=InstrumentType.SPOT,
            lot_size=1,
            tick_size=Decimal128(_tick_size(meta)),
            is_active=True,
            is_tradable=True,
        ).insert()

    out = {
        "contracts": len(contracts),
        "already_covered": len(covered),
        "created": len(created),
        "by_segment": per_segment,
        "skipped_forex": skipped_fx,
        "dry_run": dry_run,
    }
    logger.info("binance_catalogue_sync %s", out)
    return out
