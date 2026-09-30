"""Delete the international instruments that no longer have a price source.

MetaAPI was the only feed for the eight forex pairs and the seven index
CFDs (SPX500, NAS100, US30, UK100, DE40, JPN225, HK50). Binance quotes
none of them — its single forex pair can go a minute without a print, and
its index exposure is ETF shares (QQQ, SPY), which are listed separately
and priced in share terms, not index points.

Leaving them in place would show a frozen price on a tradable row, which
is the failure this whole migration exists to end.

REFUSES to delete anything that was ever traded: a row with a position,
an order or a closed trade against it is reported and kept, because its
history has to stay readable.

    cd backend && .venv/bin/python -m scripts.retire_dead_international [--apply]
"""

from __future__ import annotations

import asyncio
import sys

from app.core.database import init_database
from app.models.instrument import Instrument
from app.models.order import Order
from app.models.position import Position
from app.models.watchlist import WatchlistItem

DEAD_INDEX_SYMBOLS = {"SPX500", "NAS100", "US30", "UK100", "DE40", "JPN225", "HK50"}


async def main() -> None:
    apply = "--apply" in sys.argv
    await init_database()

    rows = await Instrument.find(
        {
            "$or": [
                {"segment": "FOREX"},
                {"segment": "INDICES", "symbol": {"$in": sorted(DEAD_INDEX_SYMBOLS)}},
            ]
        }
    ).to_list()

    deleted = kept = 0
    for inst in rows:
        pos = await Position.find({"instrument.token": inst.token}).count()
        orders = await Order.find({"instrument.token": inst.token}).count()
        wl = await WatchlistItem.find({"instrument_token": inst.token}).count()
        if pos or orders:
            print(f"  KEPT  {inst.symbol:10} {inst.segment:12} positions={pos} orders={orders}")
            kept += 1
            continue
        print(f"  {'DELETE' if apply else 'would delete'} {inst.symbol:10} {inst.segment:12} watchlist_rows={wl}")
        if apply:
            if wl:
                await WatchlistItem.find({"instrument_token": inst.token}).delete()
            await inst.delete()
        deleted += 1

    print(f"\n{'deleted' if apply else 'would delete'}: {deleted}   kept (has history): {kept}")
    if not apply:
        print("re-run with --apply to make the change")


if __name__ == "__main__":
    asyncio.run(main())
