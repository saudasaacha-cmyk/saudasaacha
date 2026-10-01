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
from decimal import Decimal
from typing import Any

import httpx
from bson import Decimal128

from app.models._base import Exchange, InstrumentType
from app.models.instrument import Instrument
from app.services.binance_futures_service import contract_for

logger = logging.getLogger(__name__)

_EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
_TICKER_24H_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"

# Segments this sync owns. An instrument outside these is none of its
# business — Zerodha's NSE / MCX rows must never be touched.
MANAGED_SEGMENTS = ("COMMODITIES", "STOCKS", "INDICES", "CRYPTO_SPOT")

_EQUITY_TYPES = {"EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "PREMARKET"}

# Binance files these as equities because they are ETF shares. Users look
# for them as indices.
_INDEX_ETFS = {
    "QQQ", "SPY", "IWM", "EWJ", "EWY", "EWT", "EWZ",
    "SMH", "XBI", "XLE", "GDX", "URNM", "KODEX200", "BITO",
}

# Binance's listing carries no company or asset names, only tickers — so a
# browse reads "CAT, CBRS, CIEN, COHR" with nothing to tell them apart. These
# are the ones a user is likely to meet; anything not here keeps its ticker,
# which is still what they'd search for.
_NICE_NAMES = {
    # Commodities
    "XAU": "Gold", "XAG": "Silver", "XPT": "Platinum", "XPD": "Palladium",
    "CL": "WTI Crude Oil", "BZ": "Brent Crude Oil", "NATGAS": "Natural Gas",
    # Crypto majors
    "BTC": "Bitcoin", "ETH": "Ethereum", "BNB": "BNB", "SOL": "Solana",
    "XRP": "XRP", "ADA": "Cardano", "DOGE": "Dogecoin", "TRX": "TRON",
    "LINK": "Chainlink", "AVAX": "Avalanche", "LTC": "Litecoin",
    "DOT": "Polkadot", "POL": "Polygon", "SHIB": "Shiba Inu",
    "UNI": "Uniswap", "ATOM": "Cosmos", "APT": "Aptos", "ARB": "Arbitrum",
    "OP": "Optimism", "NEAR": "NEAR Protocol", "FIL": "Filecoin",
    "SUI": "Sui", "TON": "Toncoin", "HBAR": "Hedera", "ICP": "Internet Computer",
    "BCH": "Bitcoin Cash", "ETC": "Ethereum Classic", "XLM": "Stellar",
    "AAVE": "Aave", "PEPE": "Pepe", "WIF": "dogwifhat", "BTCDOM": "Bitcoin Dominance Index",
    # US stocks
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "TSLA": "Tesla",
    "AMZN": "Amazon", "GOOGL": "Alphabet (Google)", "META": "Meta Platforms",
    "NFLX": "Netflix", "AMD": "AMD", "INTC": "Intel", "ORCL": "Oracle",
    "CRM": "Salesforce", "IBM": "IBM", "QCOM": "Qualcomm", "AVGO": "Broadcom",
    "MU": "Micron", "TSM": "TSMC", "ASML": "ASML", "AMAT": "Applied Materials",
    "LRCX": "Lam Research", "KLAC": "KLA", "TXN": "Texas Instruments",
    "ADBE": "Adobe", "PLTR": "Palantir", "COIN": "Coinbase",
    "MSTR": "MicroStrategy", "HOOD": "Robinhood", "UBER": "Uber",
    "DIS": "Disney", "KO": "Coca-Cola", "WMT": "Walmart", "COST": "Costco",
    "JPM": "JPMorgan Chase", "GS": "Goldman Sachs", "BRKB": "Berkshire Hathaway",
    "V": "Visa", "PYPL": "PayPal", "SHOP": "Shopify", "SNOW": "Snowflake",
    "CRWD": "CrowdStrike", "PANW": "Palo Alto Networks", "NET": "Cloudflare",
    "DDOG": "Datadog", "ZS": "Zscaler", "TEAM": "Atlassian", "MDB": "MongoDB",
    "CAT": "Caterpillar", "XOM": "ExxonMobil", "NKE": "Nike", "MRK": "Merck",
    "LLY": "Eli Lilly", "UNH": "UnitedHealth", "MRNA": "Moderna",
    "NVO": "Novo Nordisk", "ACN": "Accenture", "CSCO": "Cisco", "DELL": "Dell",
    "HPE": "HP Enterprise", "WDC": "Western Digital", "STX": "Seagate",
    "SMCI": "Super Micro", "ARM": "Arm Holdings", "RIVN": "Rivian",
    "CVNA": "Carvana", "GME": "GameStop", "AMC": "AMC Entertainment",
    "RDDT": "Reddit", "EBAY": "eBay", "ZM": "Zoom", "TTWO": "Take-Two",
    "DKNG": "DraftKings", "SOFI": "SoFi", "MARA": "Marathon Digital",
    "HD": "Home Depot", "PDD": "PDD Holdings", "BABA": "Alibaba",
    "TENCENT": "Tencent", "MEITUAN": "Meituan", "BYD": "BYD",
    "KUAISHOU": "Kuaishou", "SONY": "Sony", "SAMSUNG": "Samsung Electronics",
    "SKHYNIX": "SK Hynix", "HYUNDAI": "Hyundai Motor", "NAVER": "Naver",
    "LGELECTRONICS": "LG Electronics", "POPMART": "Pop Mart",
    # Private / pre-IPO
    "OPENAI": "OpenAI (pre-IPO)", "ANTHROPIC": "Anthropic (pre-IPO)",
    "SPCX": "SpaceX (pre-IPO)", "MOONSHOT": "Moonshot AI (pre-IPO)",
    "MINIMAX": "MiniMax (pre-IPO)", "ZHIPU": "Zhipu AI (pre-IPO)",
    "UNITREE": "Unitree Robotics (pre-IPO)", "OURA": "Oura (pre-IPO)",
    # Leveraged / inverse — the name has to say so
    "SOXL": "Semiconductors 3x Long (SOXL)", "SOXS": "Semiconductors 3x Short (SOXS)",
    "TQQQ": "Nasdaq 100 3x Long (TQQQ)", "SQQQ": "Nasdaq 100 3x Short (SQQQ)",
    "TSLL": "Tesla 2x Long (TSLL)", "NVDL": "Nvidia 2x Long (NVDL)",
    "UVXY": "Volatility 1.5x Long (UVXY)", "TZA": "Small Cap 3x Short (TZA)",
    "TBT": "20Y Treasury 2x Short (TBT)", "TMF": "20Y Treasury 3x Long (TMF)",
    "KORU": "Korea 3x Long (KORU)",
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
    "COPPER": "Copper",
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
        if s.get("status") == "TRADING"
        and s.get("quoteAsset") == "USDT"
        # Perpetuals only. Binance also lists dated quarterlies
        # (BTCUSDT_251226) whose base asset is just "BTC", so letting them
        # through put three Bitcoin rows in the browse — the perp, the
        # March contract and the June one, all called BTC.
        and s.get("contractType") in ("PERPETUAL", "TRADIFI_PERPETUAL")
    ]


async def fetch_turnover() -> dict[str, float]:
    """24 h quote-volume per contract, for the browse order."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(_TICKER_24H_URL)
            r.raise_for_status()
            rows = r.json()
        return {
            str(x.get("symbol")): float(x.get("quoteVolume") or 0)
            for x in rows
            if x.get("symbol")
        }
    except Exception:  # noqa: BLE001 — ranking is a nicety, listing is not
        logger.warning("binance_turnover_fetch_failed", exc_info=True)
        return {}


async def sync_catalogue(*, dry_run: bool = False) -> dict[str, Any]:
    """Add every Binance contract the catalogue doesn't already carry, and
    refresh the display name + browse rank on the ones it does.

    A row's token is never touched: that is what positions, orders and
    watchlists point at. Name and rank are display-only, so they're kept
    current on every run — a contract's turnover changes, and a name map
    that only applied to rows created after it shipped would leave the
    earliest instruments as bare tickers forever.
    """
    contracts = await fetch_contracts()
    by_symbol = {c["symbol"]: c for c in contracts}
    known = set(by_symbol)
    turnover = await fetch_turnover()
    # Rank by turnover: 0 is the most traded contract on the venue.
    ranked = sorted(turnover, key=lambda k: -turnover[k])
    rank_of = {sym: i for i, sym in enumerate(ranked)}

    existing = await Instrument.find(
        {"segment": {"$in": list(MANAGED_SEGMENTS)}}
    ).to_list()
    # Which contracts are already represented, resolved exactly the way the
    # feed resolves them.
    covered: set[str] = set()
    refreshed = 0
    for inst in existing:
        contract = contract_for(inst.symbol, known)
        if contract is None:
            continue
        covered.add(contract)
        base = str(by_symbol[contract]["baseAsset"]).upper()
        want_name = _NICE_NAMES.get(base, base)
        want_rank = rank_of.get(contract, 9999)
        # The tick has to be refreshed too, not just set on insert. Rows that
        # pre-date this sync (the old MetaAPI mirror, the seed) carry the
        # 0.05 default, and `tick_size` is what the chart turns into its
        # decimal count — so DOGE at 0.08123 drew on a 2-decimal axis and
        # looked flat. Binance's PRICE_FILTER is the real increment.
        want_tick = _tick_size(by_symbol[contract])
        # `trading_symbol` carries the contract the price comes from, so a
        # search for CLUSDT lands on USOIL and the row can show which
        # contract it is quoting.
        if (
            inst.name != want_name
            or getattr(inst, "feed_rank", 9999) != want_rank
            or inst.trading_symbol != contract
            or Decimal(str(inst.tick_size)) != Decimal(want_tick)
        ):
            refreshed += 1
            if not dry_run:
                inst.name = want_name
                inst.feed_rank = want_rank
                inst.trading_symbol = contract
                inst.tick_size = Decimal128(want_tick)
                await inst.save()
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
            feed_rank=rank_of.get(sym, 9999),
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
        "refreshed": refreshed,
        "by_segment": per_segment,
        "skipped_forex": skipped_fx,
        "dry_run": dry_run,
    }
    logger.info("binance_catalogue_sync %s", out)
    return out
