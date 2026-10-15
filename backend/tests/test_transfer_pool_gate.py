"""The two gates on the cross-admin transfer dialog: who may move a client,
and whose email the destination picker prints.

`_assert_owns` used to spell its own ownership check:

    target.assigned_admin_id == admin.id or admin.id in target.broker_ancestry

`broker_ancestry` holds BROKER ids and never ADMIN ids (see the field comment
on `User`), so with an ADMIN caller the second arm could not match a row that
has ever been written — the gate was the flat first arm wearing two. And the
flat arm is not reliable alone. `reassign_user` does re-stamp the subtree's
`assigned_admin_id` — it is there, do not go looking for it — but inside a bare
`try` with no transaction and only for rows that existed once that propagation
was added, so a partial failure or a legacy row keeps the OLD admin's id. And
the deeper descendants never carried `assigned_broker_id == <moved broker>` at
all, which is the arm that actually covers them. The new owner's Users page listed
those clients (it asks `_pool_clause`) and the transfer refused them with
"This user isn't in your pool". `_pool_clause` closes both holes, plus the
EMPLOYEE one: no `effective_scope_actor` meant an employee holding
`transfer_users` was refused on every single row.

Second gate: `/transfer/admins` returned raw `a.email` for every ADMIN on the
platform to anyone holding `transfer_users`, bypassing `user_contacts`.

No Mongo. `_pool_clause`'s one broker-lookup query is stubbed, and the
`_id` membership test is evaluated against in-memory rows by the matcher
below — the same shape-limited matcher as test_export_owner_pool.py.

    pytest -q backend/tests/test_transfer_pool_gate.py
"""

from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace
from typing import Any

from app.api.v1.admin import management as mgmt_api
from app.models.user import User, UserRole
from app.services.user_service import CONTACT_MASK

ADMIN_NEW, ADMIN_OLD, BROKER, EMPLOYEE = "A_new", "A_old", "B1", "E1"

# The client the gate refused: minted by B1 while B1 sat under A_old, then B1
# was handed to A_new. Nothing rewrote this row.
TRANSFERRED = SimpleNamespace(
    id="C1",
    assigned_admin_id=ADMIN_OLD,
    assigned_broker_id=BROKER,
    broker_ancestry=[BROKER],
)
# Someone else's client entirely — must stay refused, or the fix is a leak.
OUTSIDER = SimpleNamespace(
    id="C2", assigned_admin_id="A_other", assigned_broker_id=None, broker_ancestry=[]
)


def _actor(role: UserRole, oid: str, parent: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(role=role, id=oid, assigned_admin_id=parent)


# ── in-memory stand-in for the two queries `_assert_owns` makes ──────
def _matches(doc: SimpleNamespace, arm: dict[str, Any]) -> bool:
    """One pool-clause arm (or an `_id` equality) against one user row.

    Equality and `$in`, over a scalar or an array field, is every shape
    `_pool_clause` emits. Anything else blows up here rather than quietly
    evaluating to "matched".
    """
    ((field, cond),) = arm.items()
    if isinstance(cond, dict):
        assert set(cond) == {"$in"}, f"unhandled operator: {cond}"
        want = cond["$in"]
    else:
        want = [cond]
    val = getattr(doc, field, None) if field != "_id" else doc.id
    return any(w in val for w in want) if isinstance(val, list) else val in want


def _eval(query: dict[str, Any], doc: SimpleNamespace) -> bool:
    """Evaluate the merged query `_assert_owns` hands Mongo. Top-level keys
    AND together; `$and` entries recurse; an `$or` needs one arm."""
    for key, cond in query.items():
        if key == "$and":
            if not all(_eval(c, doc) for c in cond):
                return False
        elif key == "$or":
            if not any(_matches(doc, arm) for arm in cond):
                return False
        elif not _matches(doc, {key: cond}):
            return False
    return True


def _stub_db(monkeypatch, rows, *, brokers_of: dict[str, list[str]], parents=()):
    """Stands in for Mongo: `_admin_pool_clause`'s broker projection, the
    `_id` count, and `User.get` for EMPLOYEE parent resolution."""
    seen: list[dict] = []

    async def _agen(docs):
        for d in docs:
            yield d

    def _find(query, projection=None):
        # If this stops asking for BROKER rows of this admin, the arms the
        # clause builds mean nothing.
        assert query["role"] == UserRole.BROKER.value
        return _agen(
            [{"_id": b} for b in brokers_of.get(query["assigned_admin_id"], [])]
        )

    async def _count(query, limit=0):
        # `limit` mirrors motor's real signature — the gate passes limit=1
        # because it only asks "does one match", never "how many".
        seen.append(query)
        n = sum(1 for r in rows if _eval(query, r))
        return min(n, limit) if limit else n

    coll = SimpleNamespace(find=_find, count_documents=_count)
    monkeypatch.setattr(User, "get_motor_collection", classmethod(lambda cls: coll))
    monkeypatch.setattr(
        User, "get", classmethod(lambda cls, oid: _ok(dict(parents).get(oid)))
    )
    return seen


async def _ok(v):
    return v


def test_a_transferred_brokers_client_can_now_be_moved(monkeypatch):
    """The bug, as the operator hit it: A_new owns B1, the Users page lists
    C1, and the transfer said C1 wasn't theirs."""
    _stub_db(monkeypatch, [TRANSFERRED, OUTSIDER], brokers_of={ADMIN_NEW: [BROKER]})
    admin = _actor(UserRole.ADMIN, ADMIN_NEW)

    assert asyncio.run(mgmt_api._assert_owns(admin, TRANSFERRED)) is True
    # The old two arms, on this exact row, for this exact caller:
    assert TRANSFERRED.assigned_admin_id != ADMIN_NEW
    assert ADMIN_NEW not in TRANSFERRED.broker_ancestry


def test_someone_elses_client_is_still_refused(monkeypatch):
    """The half of the gate that was working. A wrong widening here is worse
    than the bug it replaces."""
    _stub_db(monkeypatch, [TRANSFERRED, OUTSIDER], brokers_of={ADMIN_NEW: [BROKER]})
    admin = _actor(UserRole.ADMIN, ADMIN_NEW)

    assert asyncio.run(mgmt_api._assert_owns(admin, OUTSIDER)) is False


def test_the_flat_direct_arm_still_holds_for_an_admin_with_no_brokers(monkeypatch):
    """`_pool_clause` returns a one-key equality in that case, and `_id` must
    merge flat beside it — a one-element `$and` would cost the index lookup."""
    direct = SimpleNamespace(
        id="C3", assigned_admin_id=ADMIN_NEW, assigned_broker_id=None, broker_ancestry=[]
    )
    seen = _stub_db(monkeypatch, [direct], brokers_of={})
    admin = _actor(UserRole.ADMIN, ADMIN_NEW)

    assert asyncio.run(mgmt_api._assert_owns(admin, direct)) is True
    assert seen[-1] == {"_id": "C3", "assigned_admin_id": ADMIN_NEW}


def test_an_employee_with_the_grant_is_scoped_to_its_admins_pool(monkeypatch):
    """An employee owns no clients, so its own id matched nothing and every
    row came back refused. It must act on its PARENT admin's pool."""
    parent = _actor(UserRole.ADMIN, ADMIN_NEW)
    _stub_db(
        monkeypatch,
        [TRANSFERRED, OUTSIDER],
        brokers_of={ADMIN_NEW: [BROKER]},
        parents={ADMIN_NEW: parent},  # keyed by `assigned_admin_id`, as the resolver looks it up
    )
    employee = _actor(UserRole.EMPLOYEE, EMPLOYEE, parent=ADMIN_NEW)

    assert asyncio.run(mgmt_api._assert_owns(employee, TRANSFERRED)) is True
    assert asyncio.run(mgmt_api._assert_owns(employee, OUTSIDER)) is False


def test_a_broker_caller_is_scoped_to_its_own_subtree(monkeypatch):
    """`_pool_clause` is pure for a BROKER — ancestry really does hold its id."""
    _stub_db(monkeypatch, [TRANSFERRED, OUTSIDER], brokers_of={})
    broker = _actor(UserRole.BROKER, BROKER)

    assert asyncio.run(mgmt_api._assert_owns(broker, TRANSFERRED)) is True
    assert asyncio.run(mgmt_api._assert_owns(broker, OUTSIDER)) is False


def test_the_super_admin_still_reaches_into_a_sub_admins_pool(monkeypatch):
    """Deliberately short-circuited before `_pool_clause`, which would narrow
    the platform owner to `assigned_admin_id: None` — their own book only."""
    seen = _stub_db(monkeypatch, [TRANSFERRED], brokers_of={})
    sa = _actor(UserRole.SUPER_ADMIN, "SA")

    assert asyncio.run(mgmt_api._assert_owns(sa, TRANSFERRED)) is True
    assert seen == []  # no query at all


def test_both_transfer_endpoints_route_through_the_one_gate():
    """Single and bulk must agree; the bulk loop skips instead of 403ing, and
    that difference is the only one allowed between them."""
    for fn in (mgmt_api.transfer_user_to_admin, mgmt_api.transfer_users_to_admin_bulk):
        assert "_assert_owns(admin, target" in inspect.getsource(fn)
    # The bulk path passes a pre-resolved clause — the clause depends on the
    # ACTOR, so rebuilding it per row cost one broker lookup per user. Pinned
    # because dropping the argument silently restores the N+1 rather than
    # failing anything.
    bulk_src = inspect.getsource(mgmt_api.transfer_users_to_admin_bulk)
    assert "_assert_owns(admin, target, bulk_clause)" in bulk_src
    assert bulk_src.count("_pool_clause") == 1
    assert "This user isn't in your pool" in inspect.getsource(
        mgmt_api.transfer_user_to_admin
    )


def test_the_destination_picker_masks_peer_admin_emails():
    """`transfer_users` lets an admin MOVE a client. It is not a licence to
    read every peer admin's email, which is what the raw `a.email` was."""
    src = inspect.getsource(mgmt_api.transfer_admin_targets)
    assert "can_read_contacts" in src
    assert 'contact_out(a.email, reveal=reveal)' in src
    assert '"email": a.email' not in src
    # Masked, not removed: the dialog reads `.email` for its subtitle and its
    # search box, so dropping the key would change the UI's shape.
    assert '"email"' in src
    assert len(CONTACT_MASK) > 0
