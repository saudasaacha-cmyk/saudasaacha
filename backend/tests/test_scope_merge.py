"""Scope merging, and the one place the contact dash is decided.

`scoped_user_filter` returns `{assigned_admin_id: x}` for most actors but an
`$or` for an ADMIN who has brokers. A dict holds `$or` once, so a caller that
pastes the scope in beside a search box's own `$or` keeps only one of them —
and when the one that goes is the SCOPE, nothing raises: the endpoint quietly
lists users the actor is not allowed to see. That merge used to be hand-written
in three endpoints plus a service, in three different spellings, and one of
them had already drifted.

    pytest -q backend/tests/test_scope_merge.py
"""

from __future__ import annotations

import inspect

from app.core.dependencies import merge_scope
from app.services.user_service import CONTACT_MASK, contact_display

SEARCH = {"$or": [{"email": "re"}, {"user_code": "re"}]}
POOL_OR = {
    "$or": [
        {"assigned_admin_id": "A"},
        {"assigned_broker_id": {"$in": ["B1"]}},
        {"broker_ancestry": {"$in": ["B1"]}},
    ]
}
POOL_FLAT = {"assigned_admin_id": "A"}


def test_a_scope_or_and_a_search_or_both_survive():
    """The case the helper exists for. Before: one `$or` key, so the pool
    clause vanished and the search matched the whole platform."""
    q = merge_scope({"is_demo": {"$ne": True}}, POOL_OR, SEARCH)

    assert q["$and"] == [SEARCH, POOL_OR]
    assert "$or" not in q  # neither clause was promoted over the other
    assert q["is_demo"] == {"$ne": True}


def test_a_single_key_scope_stays_a_flat_equality():
    """Most actors get a one-key scope. Wrapping that in `$and` would cost
    the index lookup for nothing, so it is merged flat."""
    q = merge_scope({"role": "CLIENT"}, POOL_FLAT)

    assert q == {"role": "CLIENT", "assigned_admin_id": "A"}


def test_a_scope_key_can_never_overwrite_one_the_caller_pinned():
    """The sub-brokers tab pins `assigned_broker_id: {$ne: None}`. If the pool
    clause is ever flattened to that same key, `update()` would drop the pin
    and list top-level brokers as sub-brokers."""
    pinned = {"role": "BROKER", "assigned_broker_id": {"$ne": None}}
    q = merge_scope(dict(pinned), {"assigned_broker_id": {"$in": ["B1"]}})

    assert q["assigned_broker_id"] == {"$ne": None}
    assert q["$and"] == [{"assigned_broker_id": {"$in": ["B1"]}}]


def test_an_absent_scope_leaves_the_query_alone():
    """The super-admin's platform-wide view passes no scope at all."""
    assert merge_scope({"role": "CLIENT"}, None) == {"role": "CLIENT"}
    assert merge_scope({"role": "CLIENT"}, {}, None) == {"role": "CLIENT"}


def test_the_hand_written_merge_is_reproduced_exactly():
    """Pure refactor: for every scope shape the resolver can return, and with
    or without a search box, the helper must produce the query the deleted
    copies produced. A 'cleanup' that changes a scope query is invisible."""

    def old(base: dict, scope: dict, search: dict | None) -> dict:
        query = dict(base)
        and_clauses = [search] if search else []
        if "$or" in scope:
            and_clauses.append(scope)
        else:
            query.update(scope)
        if and_clauses:
            query["$and"] = and_clauses
        return query

    bases = [
        {"is_demo": {"$ne": True}, "role": {"$nin": ["ADMIN"]}},  # list_users
        {"_id": {"$in": ["u1", "u2"]}},  # online list / live overview
        {"role": "BROKER", "status": {"$ne": "CLOSED"}},  # accounts tabs
    ]
    scopes = [POOL_FLAT, {"assigned_admin_id": None}, {"broker_ancestry": "B1"}, POOL_OR]
    for base in bases:
        for scope in scopes:
            for search in (None, SEARCH):
                assert merge_scope(dict(base), scope, search) == old(base, scope, search)


def test_the_one_input_where_the_helper_deliberately_differs():
    """Honesty about the matrix above: it holds the base queries and the
    scope shapes APART, so the single input where old and new disagree
    cannot appear in it. Stating it here instead of implying it away.

    The old flat path was `query.update(scope)`, where a scope key
    OVERWRITES one the caller pinned — silently widening or narrowing by
    whichever side happened to be applied last. The helper ANDs them, so
    both survive. That is a real difference, and it is the safe
    direction: a caller's filter can no longer be dropped.

    It changes no endpoint today — no base query at the six converted
    sites pins a key `_pool_clause` can return — which is why the matrix
    above is still a fair proof of "no behaviour changed", as long as
    this case is named rather than omitted.
    """
    collides = {"assigned_admin_id": "A1"}
    base = {"assigned_admin_id": "SOMEONE_ELSE"}

    # Old: the scope wins, the caller's own filter is gone.
    assert dict(base, **collides) == {"assigned_admin_id": "A1"}
    # New: both are required.
    merged = merge_scope(dict(base), collides)
    assert merged["assigned_admin_id"] == "SOMEONE_ELSE"
    assert {"assigned_admin_id": "A1"} in merged["$and"]


def test_no_list_endpoint_merges_a_scope_by_hand_any_more():
    """The point of the exercise: one implementation, so the next change to
    the scope shape cannot miss a copy."""
    from app.api.v1.admin import accounts, users
    from app.services import active_users_service

    for mod in (users, accounts, active_users_service):
        src = inspect.getsource(mod)
        assert "update(scope" not in src
        assert "update(admin_scope" not in src
        assert '"$or" in scope' not in src


def test_a_placeholder_contact_shows_as_a_dash_not_a_fake_address():
    """`cl82066844@noemail…` is an ABSENCE, not an address — in the panel, in
    the sheet and in the PDF alike."""
    assert contact_display("cl82066844@noemail.sachchasauda.com", reveal=True) == "—"
    assert contact_display("NOMOBCL82066844", reveal=True) == "—"
    assert contact_display(None, reveal=True) == "—"
    assert contact_display("", reveal=False) == "—"


def test_a_real_contact_is_masked_until_granted():
    """Same `user_contacts` rule as `contact_out` — the dash is the only
    thing this wrapper adds."""
    assert contact_display("suresh@gmail.com", reveal=True) == "suresh@gmail.com"
    assert contact_display("suresh@gmail.com", reveal=False) == CONTACT_MASK
    assert "gmail" not in contact_display("suresh@gmail.com", reveal=False)


def test_the_export_no_longer_re_implements_the_rule():
    """The export's own copy took no `reveal` argument, so a new placeholder
    family would have kept printing real contacts into the sheet."""
    from app.services import user_export_service

    src = inspect.getsource(user_export_service)
    assert "contact_display" in src
    assert '"—" if' not in src
