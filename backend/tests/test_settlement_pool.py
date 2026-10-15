"""Whose P&L the weekly sub-admin settlement is computed over.

`compute_settlement` used to build its own user list from a flat
`{assigned_admin_id: sub_admin_id}` find(). Two things were wrong with that,
and only one of them was visible:

  * MISSING money. `_admin_pool_clause` — what every other money view
    resolves through — also claims a client reached via `assigned_broker_id`
    or `broker_ancestry` under one of the admin's brokers. The flat stamp
    alone misses those whenever a BROKER transfer's subtree re-stamp didn't
    fully land (no transaction around it; and it only reaches rows that
    carry the broker in `broker_ancestry`). Those clients keep trading under
    the admin's broker while their realized P&L lands in nobody's
    settlement. That is the number an admin gets paid on, and it was short,
    silently, with no error anywhere.
  * JUNK in the pool. The flat query carried none of the
    `_NON_CLIENT_ROLES` / `is_demo` / `status` conditions every other money
    view has, so the admin's own BROKER and EMPLOYEE login rows and its demo
    accounts were counted as settled users. Zero P&L today — a wrong
    settlement the first time anyone trades a demo account.

`scoped_user_ids` is the canonical resolver for both halves, and
`_sub_admin_user_ids` now delegates to it. The matcher below is a 20-line
stand-in for Mongo's query evaluator (equality, $in/$nin/$ne, $or/$and, and
multikey list fields), which is all the pool clause uses — so the settlement's
own resolver runs against the real pool clause and the real role/demo filters
with no database.

ORDERING CAVEAT for whoever ships this: on rows where the broker-transfer
`$pull` of stale `broker_ancestry` has not been applied yet, a transferred
client matches BOTH tenants' pool clauses, so its P&L would now be settled
twice. Narrowing this function back is not the answer — every other money view
already has that exposure, this one was simply the odd one out. Run
`python -m scripts.backfill_broker_ancestry` first.

    pytest -q backend/tests/test_settlement_pool.py
"""

from __future__ import annotations

import ast
import asyncio
import inspect

from app.core.dependencies import scoped_user_ids
from app.models.user import User, UserRole, UserStatus
from app.services import admin_settlement_service as stl

A1 = "admin-1"  # the sub-admin being settled
A2 = "admin-2"  # some other tenant
B1 = "broker-1"  # created under A1
B2 = "broker-2"  # created under A2, later TRANSFERRED to A1

# One row per user, spelled the way Mongo holds them.
ROWS = [
    {"_id": A1, "role": UserRole.ADMIN.value},
    {"_id": A2, "role": UserRole.ADMIN.value},
    {"_id": B1, "role": UserRole.BROKER.value, "assigned_admin_id": A1},
    {"_id": B2, "role": UserRole.BROKER.value, "assigned_admin_id": A1},
    {"_id": "c-direct", "role": UserRole.CLIENT.value, "assigned_admin_id": A1},
    {
        "_id": "c-under-b1",
        "role": UserRole.CLIENT.value,
        "assigned_admin_id": A1,
        "assigned_broker_id": B1,
        "broker_ancestry": [B1],
    },
    # THE BUG: B2 moved to A1, this client's assigned_admin_id still says A2.
    {
        "_id": "c-under-transferred-b2",
        "role": UserRole.CLIENT.value,
        "assigned_admin_id": A2,
        "assigned_broker_id": B2,
        "broker_ancestry": [B2],
    },
    {
        "_id": "c-closed",
        "role": UserRole.CLIENT.value,
        "assigned_admin_id": A1,
        "status": UserStatus.CLOSED.value,
    },
    {
        "_id": "c-demo",
        "role": UserRole.CLIENT.value,
        "assigned_admin_id": A1,
        "is_demo": True,
    },
    {"_id": "emp", "role": UserRole.EMPLOYEE.value, "assigned_admin_id": A1},
    {"_id": "c-other-tenant", "role": UserRole.CLIENT.value, "assigned_admin_id": A2},
]


def _clause(doc: dict, key: str, cond) -> bool:
    if key == "$or":
        return any(_match(doc, c) for c in cond)
    if key == "$and":
        return all(_match(doc, c) for c in cond)
    raw = doc.get(key)
    vals = raw if isinstance(raw, list) else [raw]  # multikey array field
    if not isinstance(cond, dict):
        return any(v == cond for v in vals)
    return (
        ("$in" not in cond or any(v in cond["$in"] for v in vals))
        and ("$nin" not in cond or not any(v in cond["$nin"] for v in vals))
        and ("$ne" not in cond or not any(v == cond["$ne"] for v in vals))
    )


def _match(doc: dict, flt: dict) -> bool:
    return all(_clause(doc, k, v) for k, v in flt.items())


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        async def gen():
            for d in self._docs:
                yield d

        return gen()


class _Coll:
    def find(self, flt, projection=None):
        return _Cursor([r for r in ROWS if _match(r, flt)])


class _Actor:
    """Enough of a User for the pool helpers: ADMIN never hits the DB."""

    role = UserRole.ADMIN
    id = A1


def _settled(monkeypatch) -> set[str]:
    """What the settlement actually sums P&L over, via its own resolver."""
    monkeypatch.setattr(User, "get_motor_collection", staticmethod(_Coll))
    got = set(asyncio.run(stl._sub_admin_user_ids(_Actor())))
    # Liveness: an exclusion assertion is vacuously true on an empty set, so
    # a resolver that returns nothing must not be able to pass any test here.
    assert "c-direct" in got, f"resolver found no clients at all: {got}"
    return got


def _old_flat_query() -> set[str]:
    """What the deleted local helper returned, verbatim."""
    return {r["_id"] for r in ROWS if _match(r, {"assigned_admin_id": A1})}


def test_a_transferred_brokers_clients_are_in_the_settlement(monkeypatch):
    """The money. Realized P&L under a broker that moved tenants belongs to
    the admin who holds the broker NOW, not to the stale stamp on the row."""
    got = _settled(monkeypatch)

    assert "c-under-transferred-b2" in got
    assert "c-under-transferred-b2" not in _old_flat_query()


def test_the_pool_is_exactly_the_admins_trading_clients(monkeypatch):
    """Pinned whole, so a later arm added to the pool clause has to come
    past this test rather than quietly change what an admin is paid."""
    assert _settled(monkeypatch) == {
        "c-direct",
        "c-under-b1",
        "c-under-transferred-b2",
        "c-closed",
    }


def test_broker_and_employee_logins_and_demos_are_not_settled_users(monkeypatch):
    """`user_count` on the settlement row counted these, and their P&L would
    have counted too the day a demo account is traded."""
    got = _settled(monkeypatch)
    old = _old_flat_query()

    for junk in (B1, B2, "emp", "c-demo"):
        assert junk not in got
        assert junk in old  # every one of them was in the old number


def test_a_closed_user_still_owes_for_the_week_it_traded(monkeypatch):
    """Why `include_closed=True`: a user deleted on Friday traded Mon-Thu and
    the house kept that money. A settlement is a financial record of a past
    period, not a snapshot of who still exists."""
    assert "c-closed" in _settled(monkeypatch)

    # The default is the other way round, so this is a choice, not a leftover.
    monkeypatch.setattr(User, "get_motor_collection", staticmethod(_Coll))
    assert "c-closed" not in set(asyncio.run(scoped_user_ids(_Actor())))


def test_another_tenants_client_is_in_neither(monkeypatch):
    """The one thing the flat query got right stays right."""
    assert "c-other-tenant" not in _settled(monkeypatch)
    assert "c-other-tenant" not in _old_flat_query()


def test_the_settlement_resolves_its_pool_through_the_shared_helper():
    """No local copy to drift: the flat query is gone from the module, not
    just unused. An `assigned_admin_id` string literal reappearing here is
    this bug growing back."""
    assert "await scoped_user_ids(sa, include_closed=True)" in inspect.getsource(stl._sub_admin_user_ids)

    literals = {
        n.value
        for n in ast.walk(ast.parse(inspect.getsource(stl)))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    assert "assigned_admin_id" not in literals
