"""Whoever can be SHOWN a bank account must be told when it changes.

Two walks have to be mirrors of each other and were not:

  • `user/wallet.py::company_banks` resolves which account a user sees by
    walking UP — immediate broker → every parent in `broker_ancestry`,
    tip to root → assigned admin → platform default — and stops at the
    first owner with rows. `crypto_config_service.resolve_for_user` does
    the same walk.
  • `notification_service.notify_payment_details_changed` fanned out on
    `assigned_broker_id == actor.id` for a BROKER: direct clients only.

So a sub-broker that never authored a bank row inherits its parent
broker's. Its clients deposit into THAT account, and when the parent
broker edited it they were not told. Nobody sees an error; the money
goes to whichever account the user remembered, which is the one that
just changed. The ADMIN arm had the same hole one tier up (a broker
chain with no rows anywhere falls through to the admin) plus the stale
`assigned_admin_id` of a transferred broker's subtree, and the else-arm
also swallowed EMPLOYEE actors — `assigned_admin_id == employee.id` is
set on nobody, so an employee's bank edit notified zero users.

`_pool_clause` is that mirror for all four roles at once. Pure: the
BROKER and SUPER_ADMIN arms touch no database, and the clause shapes are
simple enough to match by hand.

    pytest -q backend/tests/test_payment_notice_subtree.py
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import textwrap
from types import SimpleNamespace

from app.api.v1.user import wallet as user_wallet
from app.core.dependencies import _pool_clause, effective_scope_actor
from app.models.user import UserRole
from app.services import crypto_config_service
from app.services.notification_service import notify_payment_details_changed

BROKER = SimpleNamespace(role=UserRole.BROKER, id="B", assigned_admin_id="A")
SUPER = SimpleNamespace(role=UserRole.SUPER_ADMIN, id="SA", assigned_admin_id=None)

# A sub-broker's client. The sub-broker SB authored no bank row, so the
# deposit screen shows broker B's — see the cascade in company_banks.
SUB_BROKER_CLIENT = {
    "assigned_admin_id": "A",
    "assigned_broker_id": "SB",
    "broker_ancestry": ["B", "SB"],
}
DIRECT_CLIENT = {
    "assigned_admin_id": "A",
    "assigned_broker_id": "B",
    "broker_ancestry": ["B"],
}


def _body() -> ast.Module:
    """The notifier's code with its docstring dropped — the docstring names
    the very fields these tests assert are gone from the query."""
    fn = ast.parse(
        textwrap.dedent(inspect.getsource(notify_payment_details_changed))
    ).body[0]
    stmts = fn.body[1:] if ast.get_docstring(fn) else fn.body
    return ast.Module(body=stmts, type_ignores=[])


def _called_names() -> set[str]:
    return {
        n.func.id
        for n in ast.walk(_body())
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }


def _attrs() -> set[str]:
    return {n.attr for n in ast.walk(_body()) if isinstance(n, ast.Attribute)}


def _literals() -> set[str]:
    return {
        n.value
        for n in ast.walk(_body())
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def _matches(clause: dict, doc: dict) -> bool:
    """The Mongo subset these pool clauses actually use: flat equality,
    `$in`, `$or`, and array-contains on a multikey field."""
    if "$or" in clause:
        return any(_matches(c, doc) for c in clause["$or"])
    for key, want in clause.items():
        have = doc.get(key)
        if isinstance(want, dict) and "$in" in want:
            hit = (
                any(v in want["$in"] for v in have)
                if isinstance(have, list)
                else have in want["$in"]
            )
        elif isinstance(have, list):
            hit = want in have
        else:
            hit = have == want
        if not hit:
            return False
    return True


def test_the_old_broker_arm_really_did_miss_the_sub_brokers_clients():
    """The premise, stated as a fact about the data model rather than a
    claim: `broker_ancestry` is the only field carrying a non-immediate
    broker, so a direct-link clause cannot see one tier down."""
    old = {"assigned_broker_id": BROKER.id}

    assert _matches(old, DIRECT_CLIENT)
    assert not _matches(old, SUB_BROKER_CLIENT)


def test_a_brokers_notice_now_reaches_the_whole_subtree():
    clause = asyncio.run(_pool_clause(BROKER))

    assert _matches(clause, DIRECT_CLIENT)
    assert _matches(clause, SUB_BROKER_CLIENT)


def test_the_platform_notice_still_stops_at_the_platform_pool():
    """Widening is right for a broker and wrong here: a sub-admin's users
    must never be told about the super-admin's bank, because the cascade
    deliberately shows them nothing rather than leaking it."""
    clause = asyncio.run(_pool_clause(SUPER))

    assert clause == {"assigned_admin_id": None}
    assert not _matches(clause, SUB_BROKER_CLIENT)


def test_the_fanout_is_built_from_the_pool_clause_not_by_hand():
    """Red on revert. The hand-rolled arms are what missed the subtree and
    swallowed EMPLOYEE; re-spelling them here would drift again silently.
    AST and not a grep, because the docstring still names those fields to
    explain why they are gone."""
    assert "_pool_clause" in _called_names()
    # `assigned_broker_id` is the arm whose hand-rolled copy missed the
    # sub-broker subtree — it must never come back here.
    assert "assigned_broker_id" not in _literals()
    # `assigned_admin_id` appears EXACTLY once, and only as the EMPLOYEE
    # union. That one is not a re-implementation of the pool, it is the one
    # row set `_pool_clause` cannot reach: `POST /admin/users` stamps an
    # employee-created client with the EMPLOYEE's own id (users.py:941),
    # while `_pool_clause` resolves an employee to its PARENT admin. Those
    # orphans read the employee's own crypto-config row, so dropping them
    # means a stale deposit address with nobody told.
    assert "assigned_admin_id" in _literals()
    src = inspect.getsource(notify_payment_details_changed)
    # `UserRole.EMPLOYEE` is an attribute, not a string literal, so this one
    # is checked against the source: the lone arm must be GUARDED by the
    # role, never applied to everyone.
    assert "UserRole.EMPLOYEE" in src
    # Counted over AST constants, not the source text — the docstring names
    # the field too, which is the whole reason this file reads the tree.
    tree = ast.parse(textwrap.dedent(src))
    uses = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and n.value == "assigned_admin_id"
    ]
    assert len(uses) == 1, (
        "a second hand-rolled assigned_admin_id means the pool is being "
        "re-implemented, which is how this drifted the first time"
    )


def test_the_pool_clause_is_merged_not_pasted():
    """The ADMIN arm is an `$or`. `query.update(clause)` beside any other
    `$or` keeps one of the two and raises nothing — on this path that
    means a money alert blasted at the wrong pool."""
    assert "merge_scope" in _called_names()
    assert "update" not in _attrs()


def test_an_employee_actor_is_resolved_rather_than_matching_nobody():
    assert "effective_scope_actor" in inspect.getsource(_pool_clause)
    assert "EMPLOYEE" in inspect.getsource(effective_scope_actor)


def test_both_resolvers_still_walk_the_ancestry_upward():
    """This pins the premise. If either resolver is ever narrowed to the
    immediate broker, the notice may narrow with it — and this test is
    where someone finds that out."""
    for fn in (user_wallet.company_banks, crypto_config_service.resolve_for_user):
        src = inspect.getsource(fn)
        assert "broker_ancestry" in src
        assert "reversed" in src
