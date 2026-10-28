"""The floating-P&L lookup the carry gate feeds on, against a real Mongo.

`carry_capacity` is pure and tested without a database. What is NOT pure is
the query that finds each user's floating P&L, and that query has a failure
mode worth a test of its own: `Position.user_id` is a `PydanticObjectId`, so
an `$in` built from the wrong type matches NOTHING, every user scores a
floating P&L of zero, and the gate silently degrades back to the cash-only
behaviour this change exists to replace. Nothing would raise. The tests would
pass. The only symptom would be force-closes that never happen.

So this runs the real query against a real server and asserts the sums.

    pytest -q backend/tests/test_carry_capacity_db.py
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
import pytest_asyncio
from beanie import PydanticObjectId, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models._base import OrderAction, ProductType
from app.models.position import Position, PositionStatus
from app.services.position_service import carry_capacity, convert_intraday_to_carry

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function")
async def db():
    client = AsyncIOMotorClient(settings.MONGODB_URL, tz_aware=True)
    name = f"{settings.MONGODB_DB_NAME}_test_carry_capacity"
    try:
        await client.admin.command("ping")
    except Exception:  # noqa: BLE001
        pytest.skip("no MongoDB reachable")
    await init_beanie(database=client[name], document_models=[Position])
    try:
        yield client[name]
    finally:
        await client.drop_database(name)
        client.close()


def _pos(user_id: PydanticObjectId, segment: str, pnl: str, status=PositionStatus.OPEN):
    """An open position carrying a known unrealized P&L."""
    return Position(
        user_id=user_id,
        instrument={
            "token": f"T{abs(hash((segment, pnl))) % 100000}",
            "symbol": "TESTSYM",
            "name": "Test",
            "segment": segment,
            "exchange": "NSE",
            "lot_size": 1,
            "tick_size": "0.05",
        },
        segment_type=segment,
        product_type=ProductType.MIS,
        side=OrderAction.BUY,
        quantity=1,
        average_price=Decimal("100"),
        margin_used=Decimal("100"),
        unrealized_pnl=Decimal(pnl),
        status=status,
        opened_at=datetime.now(UTC),
    )


async def _floating_by_user(user_ids):
    """EXACTLY the query convert_intraday_to_carry runs. Kept in step with
    it by `test_the_production_query_shape_is_what_is_tested` below."""
    out: dict = {}
    for p in await Position.find(
        {"status": PositionStatus.OPEN.value, "user_id": {"$in": list(user_ids)}}
    ).to_list():
        out[p.user_id] = out.get(p.user_id, Decimal(0)) + Decimal(str(p.unrealized_pnl or 0))
    return out


async def test_the_lookup_actually_matches_rows(db):
    """The whole point. A type mismatch here returns {} and the feature
    becomes a silent no-op."""
    uid = PydanticObjectId()
    await _pos(uid, "NFO", "250").insert()
    got = await _floating_by_user([uid])
    assert got.get(uid) == Decimal("250"), "the $in matched nothing — gate is a no-op"


async def test_profit_and_loss_net_against_each_other(db):
    uid = PydanticObjectId()
    await _pos(uid, "NFO", "900").insert()
    await _pos(uid, "MCX", "-400").insert()
    got = await _floating_by_user([uid])
    assert got[uid] == Decimal("500")


async def test_it_spans_segments_not_just_the_rolled_one(db):
    """Equity is wallet-level: a loss running in MCX has to count against an
    NFO carry. If this ever narrows to one segment, this fails."""
    uid = PydanticObjectId()
    await _pos(uid, "NFO", "100").insert()
    await _pos(uid, "MCX", "-700").insert()
    assert (await _floating_by_user([uid]))[uid] == Decimal("-600")


async def test_closed_positions_do_not_count(db):
    """Realised P&L is already in the wallet. Counting a closed row would
    credit it twice."""
    uid = PydanticObjectId()
    await _pos(uid, "NFO", "100").insert()
    await _pos(uid, "NFO", "5000", status=PositionStatus.CLOSED).insert()
    assert (await _floating_by_user([uid]))[uid] == Decimal("100")


async def test_users_do_not_bleed_into_each_other(db):
    """One user's profit must never back another user's carry."""
    a, b = PydanticObjectId(), PydanticObjectId()
    await _pos(a, "NFO", "1000").insert()
    await _pos(b, "NFO", "-1000").insert()
    got = await _floating_by_user([a, b])
    assert got[a] == Decimal("1000") and got[b] == Decimal("-1000")


async def test_end_to_end_a_loss_shrinks_the_gate(db):
    """The behaviour change, start to finish: same wallet, same cash, and
    the open loss is what decides whether ₹1200 of overnight requirement is
    backed."""
    uid = PydanticObjectId()
    await _pos(uid, "NFO", "-400").insert()
    wallet = SimpleNamespace(
        available_balance=Decimal("1000"),
        credit_limit=Decimal("0"),
        used_margin=Decimal("5000"),
    )
    floating = (await _floating_by_user([uid])).get(uid)

    need = Decimal("1200")
    assert carry_capacity(wallet, floating) == Decimal("600")
    assert need > carry_capacity(wallet, floating), "under-funded carry was allowed"
    # ...and with the loss recovered, the same book carries.
    assert not (need > carry_capacity(wallet, Decimal("400")))


async def test_the_production_query_shape_is_what_is_tested(db):
    """This file reimplements the query, so it can drift from the real one.
    Pin the two parts that matter: filtered by OPEN status and by a
    `user_id` `$in`."""
    src = inspect.getsource(convert_intraday_to_carry)
    window = src[src.index("floating_by_user") : src.index("for _uid, items in by_user.items():")]
    assert '"status": PositionStatus.OPEN.value' in window
    assert '"user_id": {"$in": list(by_user.keys())}' in window
