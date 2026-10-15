"""Who the user export's `owner` filter actually catches.

The picker offers every ADMIN and every BROKER under one `owner` param, and
the query behind it was one `$or` of three fields against that single id:

    {"assigned_admin_id": oid}, {"assigned_broker_id": oid}, {"broker_ancestry": oid}

`assigned_broker_id` and `broker_ancestry` only ever hold BROKER ids (see the
field comments on User), so for an ADMIN owner two of those three arms could
not match a row ever written. What they were meant to catch — the clients of
that admin's brokers — fell through arm 1 by luck, because broker creation
stamps `assigned_admin_id` down the chain. By luck, because transferring a
BROKER to another admin moves ONLY the broker row: its subtree keeps the old
admin's id, and the new admin's export silently came up short. That is the
exact hole `_admin_pool_clause` exists to close, which is why the export now
asks it instead of spelling its own clause.

No Mongo: the pool clause is pure for a BROKER actor, and for an ADMIN it
takes exactly one projection query — stubbed here, with its shape asserted.

    pytest -q backend/tests/test_export_owner_pool.py
"""

from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace
from typing import Any

from app.core.dependencies import _admin_pool_clause, _pool_clause
from app.models.user import User, UserRole
from app.services import user_export_service
from app.services.user_export_service import OWNER_ALL, OWNER_SELF, _query, collect_rows

ADMIN_NEW, ADMIN_OLD, BROKER, SUB_BROKER = "A_new", "A_old", "B1", "B2"

# The client the bug lost: minted by B1 back when B1 sat under A_old, then B1
# was handed to A_new. Nothing rewrote the client row.
TRANSFERRED = {
    "assigned_admin_id": ADMIN_OLD,
    "assigned_broker_id": BROKER,
    "broker_ancestry": [BROKER],
}
# Same subtree, one level deeper — under a sub-broker of B1. Only the
# ancestry arm can find this one.
DEEP = {
    "assigned_admin_id": ADMIN_OLD,
    "assigned_broker_id": SUB_BROKER,
    "broker_ancestry": [BROKER, SUB_BROKER],
}

OID = "a" * 24  # any parseable id; every lookup below is stubbed


def _matches(doc: dict[str, Any], arm: dict[str, Any]) -> bool:
    """Does one pool-clause arm match one user row?

    Equality and `$in`, over a scalar or an array field, is every shape
    `_pool_clause` can emit. A fourth shape should blow up here rather than
    quietly evaluate to "matched".
    """
    ((field, cond),) = arm.items()  # single-key by construction
    if isinstance(cond, dict):
        assert set(cond) == {"$in"}, f"unhandled operator: {cond}"
        want = cond["$in"]
    else:
        want = [cond]
    val = doc.get(field)
    if isinstance(val, list):
        return any(w in val for w in want)
    return val in want


def _old_arms(oid: str) -> list[dict[str, Any]]:
    """The clause this change deleted, kept so the regression is provable."""
    return [
        {"assigned_admin_id": oid},
        {"assigned_broker_id": oid},
        {"broker_ancestry": oid},
    ]


def _stub_broker_lookup(monkeypatch, broker_ids: list[str], *, owner: str) -> None:
    """Stand in for `_admin_pool_clause`'s one query: which brokers does this
    admin own? The assertions inside are the point — the lookup must ask for
    BROKER rows assigned to THIS admin, or the arms it builds mean nothing."""

    async def _agen(docs):
        for d in docs:
            yield d

    def _find(query, projection=None):
        assert query["role"] == UserRole.BROKER.value
        assert query["assigned_admin_id"] == owner
        return _agen([{"_id": b} for b in broker_ids])

    monkeypatch.setattr(User, "get_motor_collection", lambda: SimpleNamespace(find=_find))


def test_a_transferred_brokers_clients_were_invisible_to_the_old_clause():
    """The bug, stated as data: for the admin who now owns B1, not one of the
    three old arms matches either client. The sheet said the admin had no
    clients under that broker; the panel's user list said otherwise."""
    for row in (TRANSFERRED, DEEP):
        assert not any(_matches(row, arm) for arm in _old_arms(ADMIN_NEW))


def test_two_of_the_three_old_arms_could_never_match_any_admin_id():
    """Not "rarely" — never. Those two fields hold BROKER ids, so with an
    ADMIN owner the clause was a one-arm query wearing three arms, and the
    comment above it claimed the opposite."""
    for oid in (ADMIN_NEW, ADMIN_OLD):
        for arm in _old_arms(oid)[1:]:
            assert not any(_matches(row, arm) for row in (TRANSFERRED, DEEP))


def test_the_shared_clause_finds_the_whole_subtree_for_an_admin_owner(monkeypatch):
    """`_admin_pool_clause` keys arms 2 and 3 to the admin's BROKER ids, which
    is what makes them capable of matching: direct clients of B1 via
    `assigned_broker_id`, anything deeper via `broker_ancestry`."""
    _stub_broker_lookup(monkeypatch, [BROKER], owner=ADMIN_NEW)
    clause = asyncio.run(_pool_clause(SimpleNamespace(role=UserRole.ADMIN, id=ADMIN_NEW)))

    assert any(_matches(TRANSFERRED, arm) for arm in clause["$or"])
    assert any(_matches(DEEP, arm) for arm in clause["$or"])  # only the ancestry arm


def test_a_broker_owner_gets_its_own_subtree_and_nothing_admin_shaped():
    """A BROKER needs no lookup at all: the multikey ancestry index already
    spans sub-brokers and their clients, so the clause stays one equality."""
    clause = asyncio.run(_pool_clause(SimpleNamespace(role=UserRole.BROKER, id=BROKER)))

    assert clause == {"broker_ancestry": BROKER}
    assert _matches(TRANSFERRED, clause)
    assert _matches(DEEP, clause)
    # The sub-broker's own export is narrower, and that is correct.
    sub = asyncio.run(_pool_clause(SimpleNamespace(role=UserRole.BROKER, id=SUB_BROKER)))
    assert _matches(DEEP, sub)
    assert not _matches(TRANSFERRED, sub)


def test_the_export_query_keeps_its_own_filters_while_merging_the_pool(monkeypatch):
    """The pool clause IS an `$or` once the admin has brokers, and the export
    query already pins `role` / `status` / `is_demo` / `email`. Merged through
    `merge_scope`, so the scope lands in `$and` instead of overwriting or
    being overwritten — a dropped scope here exports the wrong admin's book."""
    _stub_broker_lookup(monkeypatch, [BROKER], owner=OID)

    async def _get(oid):
        return SimpleNamespace(role=UserRole.ADMIN, id=OID)

    monkeypatch.setattr(User, "get", _get)
    q = asyncio.run(_query(OID, include_demo=False, include_closed=False))

    assert q["role"] == UserRole.CLIENT.value
    assert q["is_demo"] == {"$ne": True}
    assert "$or" not in q  # not pasted over the top level
    (scope,) = q["$and"]
    assert len(scope["$or"]) == 3


def test_an_owner_that_is_neither_admin_nor_broker_exports_nothing(monkeypatch):
    """`owner_options` only ever offers admins and brokers. A hand-typed id
    for a client — or for a row that has since been deleted — must come back
    empty, not fall through to every client on the platform under a title
    reading "Selected owner"."""

    async def _missing(oid):
        return None

    monkeypatch.setattr(User, "get", _missing)
    assert asyncio.run(_query(OID, include_demo=False, include_closed=False))["_id"] == {"$in": []}

    async def _client(oid):
        return SimpleNamespace(role=UserRole.CLIENT, id=OID)

    monkeypatch.setattr(User, "get", _client)
    assert asyncio.run(_query(OID, include_demo=False, include_closed=False))["_id"] == {"$in": []}


def test_the_two_special_owners_are_untouched():
    """`all` is unscoped and `self` means DIRECT clients — the broker pin on
    `self` is not redundant, because a top-level broker created by the super
    admin also has `assigned_admin_id = None`, and so do its clients."""
    whole = asyncio.run(_query(OWNER_ALL, include_demo=True, include_closed=True))
    assert whole == {"role": UserRole.CLIENT.value}

    direct = asyncio.run(_query(OWNER_SELF, include_demo=False, include_closed=False))
    assert direct["assigned_admin_id"] is None
    assert direct["assigned_broker_id"] is None
    assert _matches(TRANSFERRED, {"assigned_broker_id": BROKER})  # i.e. not direct


def test_the_export_does_not_hand_roll_an_owner_clause_any_more():
    """One implementation of "what is this owner's book", so the next change
    to the ownership model cannot miss this copy of it."""
    src = inspect.getsource(user_export_service._query)

    assert "_pool_clause" in src
    assert "merge_scope" in src
    assert '{"assigned_broker_id": oid}' not in src
    assert '{"broker_ancestry": oid}' not in src
    # Resolving the owner needs a round trip, so the one caller must await it.
    assert inspect.iscoroutinefunction(_query)
    assert "await _query(" in inspect.getsource(collect_rows)


def test_the_stale_assigned_admin_id_still_shows_under_the_previous_admin():
    """Honesty about what this change does NOT fix, so nobody reads the tests
    above as a clean-ownership guarantee.

    `_admin_pool_clause` keeps arm 1 — `assigned_admin_id == me` — so until
    the transfer backfills the subtree, A_old's export ALSO lists these two
    clients. Over-inclusion for the previous owner, where the bug was
    under-inclusion for the current one. It is the shared helper's behaviour,
    which means the export, the Users page and the dashboard counts now agree
    with each other; fixing it belongs in the reassign endpoint (backfill the
    subtree's `assigned_admin_id`), not in a fourth private copy here.
    """
    assert _matches(TRANSFERRED, {"assigned_admin_id": ADMIN_OLD})
    assert '{"assigned_admin_id": admin_id}' in inspect.getsource(_admin_pool_clause)
