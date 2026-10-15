"""What the T&C cascade is allowed to reset, and that it runs at all.

`PUT /admin/support/terms` resets `terms_accepted_at` on downstream clients
so they re-accept the new text. Three things had gone wrong in that one
block, and none of them raised anything a human would see:

  • it imported `UserRole` from `app.models._base`, which does not export
    it — so every save with changed text raised ImportError OUTSIDE the
    task's try, 500'd after the text was already persisted, and nobody
    downstream was ever reset;
  • the ADMIN arm matched `assigned_admin_id` only, so clients under a
    broker that had been moved between admins (stale `assigned_admin_id`,
    the case `_admin_pool_clause`'s third arm exists for) kept trading on
    terms they were never shown, with an accept marker saying otherwise;
  • EMPLOYEE and SUPER_ADMIN fell through to a sweep over EVERY client,
    which erased acceptance markers for text those clients cannot even
    resolve.

Source- and signature-level, like test_scope_merge.py: the merge is a pure
function and the other two are structural — neither needs a database.

    pytest -q backend/tests/test_terms_cascade.py
"""

from __future__ import annotations

import ast
import importlib
import inspect
import textwrap

from app.api.v1.admin.support import set_my_terms
from app.core.dependencies import ADMIN_ROLES, merge_scope
from app.models.user import UserRole

SRC = textwrap.dedent(inspect.getsource(set_my_terms))
TREE = ast.parse(SRC)

# The three shapes `scoped_user_filter` can hand the cascade, verbatim from
# `_pool_clause` / `_admin_pool_clause`.
SUPER_POOL = {"assigned_admin_id": None}
BROKER_POOL = {"broker_ancestry": "B1"}
ADMIN_POOL = {
    "$or": [
        {"assigned_admin_id": "A"},
        {"assigned_broker_id": {"$in": ["B1"]}},
        {"broker_ancestry": {"$in": ["B1"]}},
    ]
}


def _cascade() -> ast.AsyncFunctionDef:
    for node in ast.walk(TREE):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_cascade_reset":
            return node
    raise AssertionError("the background cascade is gone")


def test_every_app_level_import_in_the_endpoint_actually_resolves():
    """The bug that made the whole cascade dead code. A function-local
    `from app.models... import X` is only executed on the request that
    needs it, so a wrong module name ships green and 500s in production
    after the save has already been written."""
    seen = 0
    for node in ast.walk(TREE):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        mod = importlib.import_module(node.module)
        for alias in node.names:
            assert hasattr(mod, alias.name), f"{node.module} has no {alias.name}"
            seen += 1
    assert seen or "import asyncio" in SRC  # stdlib-only is fine; silence isn't


def test_the_cascade_body_is_entirely_inside_its_own_guard():
    """It runs under `asyncio.create_task` with nothing awaiting it, so an
    await that escapes the `try` surfaces as an unretrieved-exception log
    at interpreter shutdown, if at all. Any statement added beside the
    `try` is invisible the same way the bad import was."""
    body = _cascade().body
    assert len(body) == 1 and isinstance(body[0], ast.Try), (
        "every statement in _cascade_reset must sit inside the try"
    )
    assert "logging.getLogger(__name__).exception" in SRC  # and failures still log


def test_the_role_filter_survives_every_pool_shape():
    """Point of `merge_scope` here: the ADMIN clause IS an `$or` and a dict
    holds `$or` once, so a literal `{"role": CLIENT, **pool}` would drop one
    half. If the dropped half is the role, this update blanks
    `terms_accepted_at` on ADMIN / BROKER rows too."""
    for pool in (SUPER_POOL, BROKER_POOL, ADMIN_POOL):
        q = merge_scope({"role": UserRole.CLIENT.value}, pool)
        assert q["role"] == UserRole.CLIENT.value

    merged = merge_scope({"role": UserRole.CLIENT.value}, ADMIN_POOL)
    assert merged["$and"] == [ADMIN_POOL]  # all three arms, none promoted
    assert "$or" not in merged


def test_the_cascade_scopes_by_the_shared_helper_and_nothing_else():
    """One `update_many`, one filter, built by the helper that owns the
    transferred-broker arm. A second branch here is how the ADMIN arm
    drifted from `scoped_user_filter` in the first place."""
    # unparse, not the raw source: comments here name the very keys the
    # code must no longer carry.
    cascade_src = ast.unparse(_cascade())
    assert cascade_src.count("update_many") == 1
    assert "await scoped_user_filter(admin)" in cascade_src
    assert "merge_scope(" in cascade_src
    # `broker_ancestry` is the helper's business and must never be
    # hand-rolled here again — that is how the ADMIN arm drifted. The one
    # assignment key this function may still name is the EMPLOYEE case
    # below, which is a DIFFERENT row set from any pool clause.
    assert "broker_ancestry" not in cascade_src
    assert cascade_src.count("assigned_admin_id") == 1


def test_an_employee_save_resets_that_employees_own_clients():
    """EMPLOYEE is in ADMIN_ROLES, so an employee reaches this endpoint.

    An earlier version of this fix returned early here, on the premise that
    no client's chain ever walks to an employee row. It does:
    `POST /admin/users` picks the ownership chain with
    `if SUPER_ADMIN / elif BROKER / else: # ADMIN` and an employee actor
    falls into that else, so the client is stamped with the EMPLOYEE's id
    (users.py:941-944 — there is no `effective_scope_actor` on that path).
    `_resolve_terms_for_user` then walks
    `assigned_broker_id or assigned_admin_id`, hits the employee row first,
    and serves the EMPLOYEE's text. Returning early meant those clients
    kept an acceptance mark for text they were never shown.

    And NOT `scoped_user_filter`, which resolves an employee to the parent
    admin's pool: those clients read the PARENT's terms, which this save
    did not touch, so including them would erase valid acceptance marks."""
    assert UserRole.EMPLOYEE in ADMIN_ROLES

    cascade_src = ast.unparse(_cascade())
    # The employee arm is chosen BEFORE the write, and it is the employee's
    # own id — not a pool clause.
    emp = cascade_src.index("UserRole.EMPLOYEE")
    assert emp < cascade_src.index("update_many"), "arm must precede the write"
    assert "'assigned_admin_id': admin.id" in cascade_src
    # It must NOT simply bail out any more.
    assert "return" not in cascade_src[emp : cascade_src.index("update_many")]
    # Both arms still reach the one guarded write.
    assert cascade_src.count("update_many") == 1
