"""Remove the dated quarterly contracts an early sync let through.

Binance lists BTCUSDT_251226 beside BTCUSDT; both carry base asset "BTC",
so the browse showed three Bitcoin rows. The sync now takes perpetuals
only — this clears the ones already created.

    cd backend && .venv/bin/python -m scripts.drop_quarterly_dupes [--apply]
"""

from __future__ import annotations

import asyncio
import sys

from app.core.database import init_database
from app.models.instrument import Instrument
from app.models.order import Order
from app.models.position import Position


async def main() -> None:
    apply = "--apply" in sys.argv
    await init_database()
    rows = await Instrument.find({"token": {"$regex": r"_\d{6}$"}}).to_list()
    n = 0
    for inst in rows:
        traded = await Position.find({"instrument.token": inst.token}).count() or \
            await Order.find({"instrument.token": inst.token}).count()
        if traded:
            print(f"  KEPT {inst.token} — has history")
            continue
        print(f"  {'delete' if apply else 'would delete'} {inst.token} (symbol {inst.symbol})")
        if apply:
            await inst.delete()
        n += 1
    print(f"\n{'deleted' if apply else 'would delete'}: {n}")


if __name__ == "__main__":
    asyncio.run(main())
