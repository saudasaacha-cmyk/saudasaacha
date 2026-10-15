"""An employee must see its parent admin's brokers, not an empty page.

`list_brokers_for` dispatches on `actor.role` with SUPER_ADMIN / ADMIN /
BROKER arms and `else: return [], 0`. EMPLOYEE is an admin-tier login
(it is in `_ADMIN_TIER_ROLES`, it holds `admin_permissions`, it reaches
the endpoint) but owns no brokers of its own, so it landed in the `else`.

Two surfaces, one of them not obviously a list:

  • the Brokers page renders zero rows for an employee holding the
    `brokers` grant;
  • the create-user "place under broker" dropdown is fed by the SAME
    function with `include_sub=True`, so it has no options — the
    employee cannot put a new client under a broker at all, and the
    client silently lands in the flat admin pool instead.

`effective_scope_actor` is the canonical resolve and already fails safe:
if the parent row won't load it hands back the employee, which still
falls to the `else` and sees nothing. Structural, because the function's
tail counts rows in Mongo while the defect is entirely in the dispatch
above it.

    pytest -q backend/tests/test_broker_list_employee.py
"""

from __future__ import annotations

import ast
import inspect

from app.core.dependencies import ADMIN_ROLES, effective_scope_actor
from app.models.user import UserRole
from app.services import broker_management_service as svc

_SRC = inspect.getsource(svc)
_TREE = ast.parse(_SRC)
_FUNCS = {
    n.name: n
    for n in ast.walk(_TREE)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
}


def _lineno_of_call(fn: ast.AST, name: str) -> int | None:
    return min(
        (
            n.lineno
            for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == name
        ),
        default=None,
    )


def _lineno_of_role_read(fn: ast.AST) -> int | None:
    return min(
        (
            n.lineno
            for n in ast.walk(fn)
            if isinstance(n, ast.Attribute) and n.attr == "role"
        ),
        default=None,
    )


def test_an_employee_reaches_this_function_at_all():
    """If EMPLOYEE were not admin-tier the `else` would be unreachable and
    there would be nothing to fix. It is, so the arm is live."""
    assert UserRole.EMPLOYEE in ADMIN_ROLES


def test_the_actor_is_resolved_before_any_role_is_read():
    """Order is the whole fix. Resolving after the first `actor.role`
    comparison leaves the dispatch reading the employee's own role, which
    matches no arm."""
    fn = _FUNCS["list_brokers_for"]
    resolved = _lineno_of_call(fn, "effective_scope_actor")
    first_role_read = _lineno_of_role_read(fn)

    assert resolved is not None, "EMPLOYEE falls through to `return [], 0`"
    assert first_role_read is not None
    assert resolved < first_role_read


def test_the_resolve_is_the_canonical_one():
    """Re-reading `assigned_admin_id` by hand here would skip the
    fail-safe and drift from `_pool_clause` / `assert_user_in_scope`."""
    assert "effective_scope_actor" in inspect.getsource(svc.list_brokers_for)
    assert "EMPLOYEE" in inspect.getsource(effective_scope_actor)


def test_no_sibling_still_drops_an_unresolved_actor_on_the_floor():
    """Same shape, same silence: a role dispatch that returns an empty page
    instead of raising is indistinguishable from "you have no brokers".
    Any function in this file that does it must resolve first."""
    for name, fn in _FUNCS.items():
        src = ast.get_source_segment(_SRC, fn) or ""
        if "return [], 0" not in src:
            continue
        assert "effective_scope_actor" in src, name
