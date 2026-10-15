"""The pool clause must never be merged with a dict spread.

`_pool_clause` / `_admin_pool_clause` return the ASSIGNMENT half of an
actor's book — today `{assigned_admin_id: x}` or an `$or` over the actor's
brokers. Three callers in `dependencies.py` used to paste it in as
`{**clause, "role": ..., "status": ...}`. That is correct only by luck: the
trailing literal wins, so the day the pool clause grows a `role` or `status`
key of its own, the pin the caller wrote is silently dropped and the pool
WIDENS. Nothing raises — the count just gets bigger, which is precisely the
direction nobody notices.

Also pinned here: the sync `scoped_admin_filter` stays deleted. It returned
the flat `{assigned_admin_id: admin.id}` for ADMIN, with a docstring
claiming broker descendants come along for free — the exact assumption
`_admin_pool_clause` exists to deny, and the one that caused the
transferred-broker cross-tenant leaks. It had zero callers; one `import`
would have brought the whole bug class back.

Source-level, like test_scope_merge.py: these are dict shapes and a
deletion, neither needs a database.

    pytest -q backend/tests/test_pool_clause_merge.py
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from app.core import dependencies as deps
from app.core.dependencies import merge_scope

_SRC = Path(inspect.getfile(deps)).read_text()
_TREE = ast.parse(_SRC)

# The three callers that build a Mongo filter out of the pool clause.
_MERGING_CALLERS = (
    "scoped_user_ids",
    "count_admin_pool_clients",
    "count_admin_pool_brokers",
)

# What _admin_pool_clause actually returns, both branches.
POOL_FLAT = {"assigned_admin_id": "A"}
POOL_OR = {
    "$or": [
        {"assigned_admin_id": "A"},
        {"assigned_broker_id": {"$in": ["B1"]}},
        {"broker_ancestry": {"$in": ["B1"]}},
    ]
}


def _func(name: str) -> ast.AST:
    for node in ast.walk(_TREE):
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef) and (node.name == name):
            return node
    raise AssertionError(f"{name} not found in dependencies.py")


def test_the_dead_sync_scope_filter_stays_deleted():
    """Zero callers when it was removed. A test import is the cheap way to
    notice it coming back, since nothing else would."""
    assert not hasattr(deps, "scoped_admin_filter")
    # and no dangling :func: reference left pointing at it
    assert "scoped_admin_filter" not in _SRC


def test_no_caller_spreads_the_pool_clause_into_a_literal():
    """`{**clause, "role": ...}` is the shape that lets a future pool key
    lose to the caller's literal. merge_scope is the only safe merge."""
    for name in _MERGING_CALLERS:
        node = _func(name)
        starstars = [
            d
            for d in ast.walk(node)
            if isinstance(d, ast.Dict)
            for k in d.keys
            if k is None  # `**x` inside a dict display
        ]
        assert not starstars, f"{name} still spreads a clause into a dict"
        calls = {
            c.func.id for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        }
        assert "merge_scope" in calls, f"{name} does not merge through merge_scope"


def test_merge_scope_is_defined_above_all_three_callers():
    """It is a module-level name resolved at call time, so order cannot
    actually break imports — but a reader checking that should get the
    answer from a test, not by scrolling."""
    where = {n.name: n.lineno for n in _TREE.body if isinstance(n, ast.AsyncFunctionDef | ast.FunctionDef)}
    for name in _MERGING_CALLERS:
        assert where["merge_scope"] < where[name]


def test_the_flat_clause_still_reaches_mongo_as_a_plain_equality():
    """Most admins have no brokers, so this is the hot path for every admin
    page. Wrapping a one-key clause in `$and` would cost the index lookup."""
    q = merge_scope({"role": {"$nin": ["ADMIN"]}, "is_demo": {"$ne": True}}, POOL_FLAT)

    assert q == {
        "role": {"$nin": ["ADMIN"]},
        "is_demo": {"$ne": True},
        "assigned_admin_id": "A",
    }
    assert "$and" not in q


def test_the_or_clause_is_anded_in_instead_of_overwriting():
    """Same rows as the old `{**clause, ...}` spread — a single-element
    `$and` holding the `$or` is what `{"$or": [...], "role": ...}` meant."""
    q = merge_scope({"role": "BROKER", "status": {"$ne": "CLOSED"}}, POOL_OR)

    assert q["$and"] == [POOL_OR]
    assert q["role"] == "BROKER"
    assert "$or" not in q


def test_a_future_pool_key_can_no_longer_widen_the_count():
    """The reason for the change. If _admin_pool_clause ever returns a
    `role` of its own, the spread would have dropped the clients-only
    exclusion and counted broker/employee logins as trading clients."""
    pinned = {"role": {"$nin": ["ADMIN", "BROKER", "EMPLOYEE"]}}
    grown = {"role": "CLIENT", "assigned_admin_id": "A"}

    assert {**grown, **pinned} != {**pinned, **grown}  # the spread was order-luck
    q = merge_scope(dict(pinned), grown)

    assert q["role"] == pinned["role"]  # the exclusion survives
    assert q["$and"] == [grown]
