"""Mirror Binance's futures listing into the instrument catalogue.

    cd backend && .venv/bin/python -m scripts.sync_binance_catalogue [--dry-run]

Idempotent: instruments already present are left untouched, so running it
again after Binance lists something new adds only the new contracts.
"""

from __future__ import annotations

import asyncio
import sys

from app.core.database import init_database
from app.services.binance_catalogue_service import sync_catalogue


async def main() -> None:
    dry = "--dry-run" in sys.argv
    await init_database()
    out = await sync_catalogue(dry_run=dry)
    print(f"contracts on Binance : {out['contracts']}")
    print(f"already in catalogue : {out['already_covered']}")
    print(f"{'would create' if dry else 'created'}         : {out['created']}")
    for seg, n in sorted(out["by_segment"].items(), key=lambda kv: -kv[1]):
        print(f"    {seg:14} {n}")
    print(f"skipped (forex)      : {out['skipped_forex']}")


if __name__ == "__main__":
    asyncio.run(main())
