"""Repair the two identity faults that leave Indian instruments unpriced.

1. Subscription rows whose `symbol` is the token number (435 of 576 in prod).
   FULL mode is re-asserted BY SYMBOL, so those rows get no OHLC: day high/low
   stay 0 and the day-range order gate can't apply, and the admin panel shows a
   wall of bare numbers.
2. Catalog rows for Indian instruments carrying a symbol-style token
   (NSE_EQ_RELIANCE, MCX_FUT_*, BSE_IDX_*). The Kite feed is keyed by numeric
   token, so these can never receive a tick — 39 rows in prod, 38 of which are
   the ONLY row for that symbol, so they must be re-pointed, not deleted.

Both are resolved against Kite's own instrument catalog, so Zerodha must be
connected when this runs.

    cd backend && source .venv/bin/activate
    python -m scripts.repair_feed_identity            # dry run, changes nothing
    python -m scripts.repair_feed_identity --apply
"""

from __future__ import annotations

import asyncio
import sys

from app.core.database import close_database, init_database
from app.models.instrument import Instrument
from app.models.zerodha_settings import ZerodhaSettings
from app.services.zerodha_service import zerodha

APPLY = "--apply" in sys.argv

# Indian segments only: the Kite feed is the one keyed by numeric token.
# International segments (FOREX / STOCKS / INDICES / COMMODITIES / CRYPTO) are
# served by MetaAPI and Binance, which key off the SYMBOL — their symbol-style
# tokens are correct and must not be touched.
INDIAN_SEGMENTS = {
    "NSE_EQUITY", "BSE_EQUITY", "MCX_FUTURE", "NFO_FUTURE", "NFO_OPTION",
    "BFO_OPTION", "NSE_INDEX_OPTION_BUY", "NSE_INDEX_OPTION_SELL",
    "NSE_FUTURE", "NSE_INDEX_FUTURE", "MCX_OPTION_BUY", "MCX_OPTION_SELL",
}


async def load_catalog() -> tuple[dict[int, dict], dict[str, dict]]:
    """token -> row and SYMBOL -> row, from Kite's catalog."""
    by_token: dict[int, dict] = {}
    by_symbol: dict[str, dict] = {}
    for ex in ("NSE", "NFO", "MCX", "BSE", "BFO"):
        try:
            rows = await zerodha.fetch_instruments(ex)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {ex}: catalog fetch failed ({exc})")
            continue
        print(f"  {ex}: {len(rows)} rows")
        for r in rows:
            tok = r.get("token")
            sym = (r.get("symbol") or "").upper()
            if tok:
                by_token[int(tok)] = r
            # First spelling wins: the NSE cash row for RELIANCE, not a future.
            if sym and sym not in by_symbol:
                by_symbol[sym] = r
    return by_token, by_symbol


async def fix_subscriptions(by_token: dict[int, dict]) -> None:
    s = await ZerodhaSettings.find_one(ZerodhaSettings.apiKey != "")
    if s is None:
        print("  no connected Zerodha settings row")
        return
    subs = s.subscribedInstruments or []
    symless = [i for i in subs if str(i.symbol) == str(i.token)]
    print(f"  symbol-less rows: {len(symless)} of {len(subs)}")
    fixed = 0
    for i in symless:
        row = by_token.get(int(i.token))
        if not row or not row.get("symbol"):
            continue
        if APPLY:
            i.symbol = row["symbol"]
            i.exchange = row.get("exchange") or i.exchange
        fixed += 1
        if fixed <= 5:
            print(f"    {i.token} -> {row['symbol']} ({row.get('exchange')})")
    print(f"  {'repaired' if APPLY else 'would repair'}: {fixed}; unresolved: {len(symless) - fixed}")
    if APPLY and fixed:
        await s.save()


async def fix_ghost_instruments(by_symbol: dict[str, dict]) -> None:
    ghosts = [
        i
        for i in await Instrument.find(Instrument.is_active == True).to_list()  # noqa: E712
        if str(i.segment) in INDIAN_SEGMENTS and not str(i.token).isdigit()
    ]
    print(f"  ghost rows (Indian, symbol-style token): {len(ghosts)}")
    repointed = skipped = 0
    for g in ghosts:
        row = by_symbol.get((g.symbol or "").upper())
        if not row:
            skipped += 1
            print(f"    ? {g.token}: Kite has no symbol '{g.symbol}' — left alone")
            continue
        new_token = str(row["token"])
        clash = await Instrument.find_one(Instrument.token == new_token)
        if clash is not None:
            # A real numeric row already exists — the ghost is a duplicate.
            skipped += 1
            print(f"    = {g.token}: numeric twin {new_token} already exists — left alone")
            continue
        if repointed < 6:
            print(f"    {g.token} -> {new_token}  ({g.symbol}, {row.get('exchange')})")
        if APPLY:
            g.token = new_token
            if row.get("exchange"):
                g.exchange = row["exchange"]
            await g.save()
        repointed += 1
    print(f"  {'re-pointed' if APPLY else 'would re-point'}: {repointed}; left alone: {skipped}")


async def main() -> None:
    print(f"=== repair_feed_identity ({'APPLY' if APPLY else 'DRY RUN'}) ===")
    await init_database()
    try:
        print("Kite catalog:")
        by_token, by_symbol = await load_catalog()
        if not by_token:
            print("  catalog empty — is Zerodha connected? aborting")
            return
        print("Subscriptions:")
        await fix_subscriptions(by_token)
        print("Catalog rows:")
        await fix_ghost_instruments(by_symbol)
    finally:
        await close_database()


asyncio.run(main())
