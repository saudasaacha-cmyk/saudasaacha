"""Who may grant, deduct and see a bonus.

Every gate in the bonuses router used to decide pool membership by comparing
something to `admin.id`:

  • grant / deduct compared the client's `assigned_admin_id` — a column that
    holds ADMIN ids only. A BROKER's id is never in it, so the compare could
    not come out true and both endpoints 403'd every broker, forever; an
    EMPLOYEE holding the `bonuses` grant was 403 for the same reason (no
    `effective_scope_actor`), and a client under a transferred broker 403'd
    although every other screen lists them under this admin.
  • the listing and `_load_scoped_bonus` compared `UserBonus.admin_id`, the
    client's `assigned_admin_id` copied at grant time — so brokers and
    employees saw an empty list and 404'd every grant, and the stamp goes
    stale when a broker moves between admins.

All of it fails CLOSED, which is why nobody filed it: the feature simply does
not work for two roles. The invariant below is one AST walk — no endpoint in
this router decides scope by comparing to `admin.id` — because the next
endpoint someone adds is the one that re-introduces it.

    pytest -q backend/tests/test_bonus_scope.py
"""

from __future__ import annotations

import ast
import asyncio
import inspect
from types import SimpleNamespace

from app.api.v1.admin import bonuses
from app.core.dependencies import assert_user_in_scope, merge_scope
from app.models.user import UserRole


def _admin_id_comparisons(mod) -> list[str]:
    """Every `... <op> admin.id` comparison in the module, by enclosing def."""
    tree = ast.parse(inspect.getsource(mod))
    hits = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Compare):
                continue
            for side in [node.left, *node.comparators]:
                if (
                    isinstance(side, ast.Attribute)
                    and side.attr == "id"
                    and isinstance(side.value, ast.Name)
                    and side.value.id == "admin"
                ):
                    hits.append(fn.name)
    return hits


def test_no_endpoint_decides_pool_membership_by_comparing_to_admin_id():
    """The whole-module invariant. Was ['grant', 'deduct', '_scope',
    '_load_scoped_bonus'] — four spellings of the same wrong question."""
    assert _admin_id_comparisons(bonuses) == []


def test_grant_and_deduct_use_the_canonical_gate():
    for name in ("grant", "deduct"):
        src = inspect.getsource(getattr(bonuses, name))
        assert "assert_user_in_scope(admin, payload.user_id)" in src, name


def test_the_canonical_gate_still_carries_the_arms_the_fix_leans_on():
    """Canary on dependencies.py: routing through the helper only fixes the
    broker and employee roles for as long as the helper keeps both arms."""
    src = inspect.getsource(assert_user_in_scope)
    assert "effective_scope_actor" in src  # EMPLOYEE → parent admin's pool
    assert "broker_ancestry" in src  # BROKER actor's subtree


def test_the_grant_listing_scopes_on_the_user_not_the_stale_stamp():
    src = inspect.getsource(bonuses._scope)
    assert "scoped_user_ids" in src
    assert "admin_id" not in src.split('"""')[-1]  # not in the code, docstring aside


def test_a_super_admin_still_sees_every_pool():
    """The one branch that needs no database: unchanged, platform-wide."""
    scope = asyncio.run(bonuses._scope(SimpleNamespace(role=UserRole.SUPER_ADMIN)))
    assert scope == {}


def test_a_user_id_filter_cannot_evict_the_pool_clause():
    """`?user_id=` pins the same key the new scope uses. A dict holds a key
    once, so `q.update(scope)` here would drop the scope and happily list
    another tenant's grants for whatever id was asked for."""
    pool = {"user_id": {"$in": ["u1", "u2"]}}
    q = merge_scope({"user_id": "SOMEONE-ELSES-CLIENT", "status": "ACTIVE"}, pool)

    assert q["user_id"] == "SOMEONE-ELSES-CLIENT"
    assert q["$and"] == [pool]  # scope survived as an AND, not overwritten


def test_both_scoped_readers_go_through_one_scope_helper():
    for fn in (bonuses.list_grants, bonuses._load_scoped_bonus):
        assert "merge_scope(" in inspect.getsource(fn)
        assert "_scope(admin)" in inspect.getsource(fn)
