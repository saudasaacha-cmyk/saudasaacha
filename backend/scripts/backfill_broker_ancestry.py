"""Repair `broker_ancestry` chains left polluted by the broker-transfer bug.

RUN THIS AFTER DEPLOYING the `reassign_user` fix — the code change only stops
NEW damage. Rows already written stay wrong until this runs.

What went wrong: `admin_management_service.reassign_user` cleared the moved
broker's OWN `assigned_broker_id` / `broker_ancestry` and re-stamped its
subtree's `assigned_admin_id`, but never removed the OLD parent brokers from
the descendants' `broker_ancestry`. Move sub-broker B2 (ancestry `[B1]`) from
admin A to admin X and client C below it keeps `broker_ancestry = [B1, B2]`.
B1 still belongs to A, so `_admin_pool_clause(A)`'s third arm and B1's own
`{"broker_ancestry": B1.id}` clause both keep matching C: C is listed under
BOTH tenants at once — user lists, dashboards, P&L, money transactions,
exports — permanently.

How the correct value is derived: NOT by patching the damaged array (it has
no record of which prefix is stale). Each user's chain is re-walked from
scratch up the `assigned_broker_id` links — user → parent → … → top broker —
and reversed into the root-first, self-excluded form documented on
`User.broker_ancestry`. The stored array is only ever COMPARED against that.

Idempotent: a second run reports 0 divergent rows. Safe to re-run after a
transfer that failed half way through.

DRY-RUN BY DEFAULT — unlike the older scripts here, which write unless given
`--dry-run`. This one rewrites tenant boundaries, so writing takes an explicit
`--apply`.

Run from the backend folder:

    cd /opt/saudasaacha/backend
    source .venv/bin/activate
    python -m scripts.backfill_broker_ancestry              # report only
    python -m scripts.backfill_broker_ancestry --apply      # write the fixes

Narrow it while verifying one complaint:

    python -m scripts.backfill_broker_ancestry --user-id 65abc...
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from beanie import PydanticObjectId
from bson import ObjectId

from app.core.database import close_database, init_database
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_broker_ancestry")

SAMPLE_LIMIT = 20


def correct_ancestry(
    user_id: ObjectId,
    parent_of: dict[ObjectId, ObjectId | None],
) -> tuple[list[ObjectId], str | None]:
    """Walk `assigned_broker_id` upward from `user_id` and return
    ``(root_first_ancestry_excluding_self, problem)``.

    `problem` is None on a clean walk, ``"cycle"`` when a broker is its own
    ancestor (the walk is abandoned — there is no correct answer to write),
    or ``"dangling:<id>"`` when a link points at a user that no longer
    exists (the chain below it is still returned; that prefix is simply all
    that can be known).
    """
    chain: list[ObjectId] = []
    seen = {user_id}
    cur = parent_of.get(user_id)
    while cur is not None:
        if cur in seen:
            return [], "cycle"
        if cur not in parent_of:
            # Parent row is gone — everything found so far is still valid,
            # the deleted broker just can't be placed above it.
            return list(reversed(chain)), f"dangling:{cur}"
        seen.add(cur)
        chain.append(cur)
        cur = parent_of.get(cur)
    return list(reversed(chain)), None


async def _main(target_user: str | None, apply: bool) -> None:
    await init_database()
    try:
        coll = User.get_motor_collection()
        # Whole-collection map first: the walk hops to arbitrary parents, so
        # per-row queries would be O(depth) round-trips each. User counts here
        # are in the tens of thousands — one pass is cheaper than the chatter.
        # ponytail: in-memory map; chunk by subtree if users ever outgrow RAM.
        rows: dict[ObjectId, dict] = {}
        async for doc in coll.find(
            {},
            {"assigned_broker_id": 1, "broker_ancestry": 1, "role": 1, "user_code": 1},
        ):
            rows[doc["_id"]] = doc
        parent_of = {uid: doc.get("assigned_broker_id") for uid, doc in rows.items()}
        logger.info("loaded %d users", len(rows))

        if target_user:
            oid = PydanticObjectId(target_user)
            if oid not in rows:
                logger.error("user %s not found", target_user)
                return
            inspect_ids = [ObjectId(oid)]
        else:
            inspect_ids = list(rows)

        divergent = 0
        fixed = 0
        cycles = 0
        dangling = 0
        samples: list[str] = []

        for uid in inspect_ids:
            doc = rows[uid]
            stored = list(doc.get("broker_ancestry") or [])
            expected, problem = correct_ancestry(uid, parent_of)

            if problem == "cycle":
                cycles += 1
                logger.warning(
                    "cycle in broker chain at user %s (%s) — left untouched, fix the "
                    "assigned_broker_id links by hand first",
                    uid,
                    doc.get("user_code"),
                )
                continue
            if problem and problem.startswith("dangling"):
                dangling += 1

            if stored == expected:
                continue

            divergent += 1
            if len(samples) < SAMPLE_LIMIT:
                samples.append(
                    f"  {doc.get('user_code') or uid} [{doc.get('role')}]  "
                    f"{[str(x) for x in stored]} → {[str(x) for x in expected]}"
                )
            if apply:
                await coll.update_one({"_id": uid}, {"$set": {"broker_ancestry": expected}})
                fixed += 1

        if samples:
            logger.info("sample of divergent rows (stored → correct):\n%s", "\n".join(samples))
        logger.info(
            "inspected=%d  divergent=%d  fixed=%d  cycles=%d  dangling_parents=%d  — %s",
            len(inspect_ids),
            divergent,
            fixed,
            cycles,
            dangling,
            "wrote the fixes" if apply else "dry run, nothing written (--apply to fix these)",
        )
    finally:
        await close_database()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", default=None, help="Only inspect this Mongo ObjectId")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Actually write the recomputed ancestries (default: report only)",
    )
    args = ap.parse_args()
    asyncio.run(_main(args.user_id, args.apply))
