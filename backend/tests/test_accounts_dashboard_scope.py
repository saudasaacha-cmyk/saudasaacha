"""What the accounts dashboard thinks an ADMIN's book is.

"Whose clients belong to this entity?" was answered THREE times for the same
admin, in three places, and the two copies in accounts_dashboard_service were
both wrong — differently:

  * `_entity_pool_ids` matched only `assigned_admin_id`, no broker arm at all.
    It feeds the KPI totals card, the Excel/PDF exports and the Positions
    Net-P&L cards, so an admin's reported totals came in UNDER the same
    admin's user list elsewhere in the app (which goes through
    `scoped_user_filter`) — and an admin whose clients all sit under their own
    brokers read as 0.
  * the per-user table had two of `_admin_pool_clause`'s three arms and was
    missing `broker_ancestry`, so every SUB-broker client was dropped.

Both now go through `_entity_scope_clause`, which asks the canonical
`_admin_pool_clause`. Source- and clause-level, like test_scope_merge.py:
the clause builders are pure for every role but ADMIN, and the ADMIN branch is
proved by what it calls — neither needs Mongo.

    pytest -q backend/tests/test_accounts_dashboard_scope.py
"""

from __future__ import annotations

import asyncio
import inspect

from app.core import dependencies as deps
from app.core.dependencies import merge_scope
from app.services import accounts_dashboard_service as ads

EID = "ADMIN_ID"
POOL_OR = {
    "$or": [
        {"assigned_admin_id": EID},
        {"assigned_broker_id": {"$in": ["B1"]}},
        {"broker_ancestry": {"$in": ["B1"]}},
    ]
}
SEARCH = {
    "$or": [
        {"user_code": {"$regex": "ra", "$options": "i"}},
        {"full_name": {"$regex": "ra", "$options": "i"}},
    ]
}


def _clause(role: str, entity_id: str = EID) -> dict:
    return asyncio.run(ads._entity_scope_clause(entity_id, role))


def test_an_admins_book_is_whatever_the_shared_helper_says(monkeypatch):
    """The whole point: no local opinion about an admin's pool. Whatever
    `_admin_pool_clause` returns is returned verbatim, for the entity asked
    about — so the dashboard can never drift from the user list again."""
    seen = []

    async def fake_pool(admin_id):
        seen.append(admin_id)
        return POOL_OR

    monkeypatch.setattr(ads, "_admin_pool_clause", fake_pool)

    assert _clause("ADMIN") == POOL_OR
    assert seen == [EID]


def test_the_shared_helper_still_carries_the_transferred_broker_arm():
    """Delegating is only worth anything while the helper keeps all three
    arms. `broker_ancestry` is the one both copies here used to miss: a broker
    reassigned to another admin leaves its subtree's `assigned_admin_id`
    stale, and sub-broker clients only ever match on ancestry."""
    src = inspect.getsource(deps._admin_pool_clause)
    for arm in ("assigned_admin_id", "assigned_broker_id", "broker_ancestry"):
        assert arm in src


def test_a_broker_entity_gets_its_whole_subtree():
    assert _clause("BROKER", "BRK1") == {"broker_ancestry": "BRK1"}


def test_a_super_admin_entity_stays_platform_wide():
    """Investigated, kept: the dashboard sends the logged-in actor's own id as
    the entity, and for a super-admin the card above it (/accounts/summary
    grand_total) counts the whole platform. `_pool_clause`'s own-book-only
    `{assigned_admin_id: None}` would make the two disagree, and the one view
    that wants the super-admin's own book asks for it by name instead."""
    assert _clause("SUPER_ADMIN") == {}
    assert _clause("SUPER_ADMIN") != {"assigned_admin_id": None}


def test_a_role_that_owns_no_pool_fails_closed():
    """An EMPLOYEE hits this branch (it logs in with the `users` grant and the
    page posts its own id). The per-user table used to add NO clause for it —
    an empty clause here means the whole platform's client list."""
    clause = _clause("EMPLOYEE", "EMP1")
    assert clause == {"assigned_broker_id": "EMP1"}
    assert clause != {}


def test_both_call_sites_ask_the_one_helper():
    """The regression that matters is a FOURTH copy appearing. Neither the
    pool-ids path nor the per-user table may name an assignment field as a
    QUERY key again — `u.assigned_broker_id` attribute reads are fine, that's
    the owner-label column, not scope."""
    for fn in (ads._entity_pool_ids, ads.get_entity_users):
        src = inspect.getsource(fn)
        assert "_entity_scope_clause" in src
        assert "merge_scope" in src
        for arm in ("assigned_admin_id", "assigned_broker_id", "broker_ancestry"):
            assert f'"{arm}"' not in src


def test_the_pool_or_and_the_search_or_both_reach_mongo():
    """Why `merge_scope` and not the old `{"$and": [user_query, ...]}` rebind:
    the pool clause IS an `$or` for an admin with brokers, and a dict holds
    `$or` once. If the pool arm is the one that goes, the search box quietly
    matches the whole platform."""
    q = merge_scope({"status": "ACTIVE", "is_demo": {"$ne": True}}, POOL_OR, SEARCH)

    assert q["$and"] == [SEARCH, POOL_OR]
    assert "$or" not in q
    assert q["status"] == "ACTIVE"
