"""Every pool-tier risk change must drop the per-user risk snapshot.

`get_effective_risk` memoises the resolved risk row per user for
RISK_CACHE_TTL (300 s) and `risk_enforcer_loop` reads it every second to
decide margin calls and stop-outs. So a pool-tier write that fails to
invalidate does not render a stale number on a page — it keeps enforcing
the OLD stop-out percentage against live positions for five minutes.

The three `upsert_*_risk` functions each walked their pool deleting one
key per user, then swept `risk:*` anyway. The three `delete_*_risk`
functions did only the walk. That mattered because the walks were wrong
in exactly the cases a pool change cares about:

  • `{assigned_broker_id: bid}` — a sub-broker's clients carry the
    parent broker in `broker_ancestry`, never here. This half is wrong
    on its own and is the load-bearing reason;
  • `{assigned_admin_id: sid}` — weaker. `reassign_user` DOES re-stamp a
    transferred subtree, so do not go hunting for a missing re-stamp; it
    just does so in a bare `try` with no transaction, after the broker
    row is saved, so a partial failure or a row predating that
    propagation keeps the old id.

So the walk was a subset of the sweep that followed it, and on the
delete paths it was the ONLY invalidation. Both halves are now the one
sweep. Source-level plus one direct call: the mutators need Mongo, the
invalidation contract does not.

    pytest -q backend/tests/test_risk_cache_wipe.py
"""

from __future__ import annotations

import ast
import asyncio
import inspect

from app.services import netting_service

_MUTATORS = (
    "upsert_sub_admin_risk",
    "delete_sub_admin_risk",
    "upsert_super_admin_risk",
    "delete_super_admin_risk",
    "upsert_broker_risk",
    "delete_broker_risk",
)

_TREE = ast.parse(inspect.getsource(netting_service))
_FUNCS = {
    n.name: n
    for n in ast.walk(_TREE)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
}


def _calls(fn_name: str) -> set[str]:
    """Names called directly inside one function, including awaited ones."""
    return {
        n.func.id
        for n in ast.walk(_FUNCS[fn_name])
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }


def test_delete_invalidates_exactly_like_upsert():
    """The asymmetry WAS the bug: save swept, delete didn't. Whatever the
    invalidation is, both halves of every tier must use the same one."""
    for tier in ("sub_admin", "super_admin", "broker"):
        assert "_wipe_pool_risk_cache" in _calls(f"upsert_{tier}_risk")
        assert "_wipe_pool_risk_cache" in _calls(f"delete_{tier}_risk")


def test_no_mutator_is_left_without_an_invalidation():
    """Guards a tier added later: six functions write pool risk rows and
    six must invalidate. A seventh that forgets is a five-minute window
    where the enforcer uses settings nobody can see any more."""
    for name in _MUTATORS:
        assert "_wipe_pool_risk_cache" in _calls(name), name


def test_the_per_pool_walks_are_gone_for_good():
    """Not cosmetic. A walk is a flat clause someone has to keep in sync
    with `_admin_pool_clause`, and getting it wrong raises nothing — it
    just leaves some users stale. There is no clause left to drift."""
    assert not [n for n in _FUNCS if n.endswith("_pool_risk_cache") and n != "_wipe_pool_risk_cache"]
    # No User query left in it — a walk needs one, a sweep doesn't. (The
    # docstring still NAMES the broken clauses, hence AST and not a grep.)
    body = ast.Module(body=_FUNCS["_wipe_pool_risk_cache"].body, type_ignores=[])
    assert not [
        n for n in ast.walk(body) if isinstance(n, ast.Attribute) and n.attr == "find"
    ]


def test_the_wipe_covers_the_whole_risk_namespace():
    """One SCAN, no pool clause to get wrong. Also the reason the walk was
    slower than what it was optimising: `cache_delete_pattern` scans the
    keyspace per call, so N users cost N scans plus the sweep's one."""
    seen: list[str] = []
    real = netting_service.cache_delete_pattern
    netting_service.cache_delete_pattern = lambda p: seen.append(p) or _noop()
    try:
        asyncio.run(netting_service._wipe_pool_risk_cache())
    finally:
        netting_service.cache_delete_pattern = real

    assert seen == ["risk:*"]


async def _noop() -> None:
    return None
