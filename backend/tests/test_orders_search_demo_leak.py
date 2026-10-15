"""The Orders monitor search box used to delete the demo-account filter.

`/admin/trading/orders` builds its query with the demo exclusion AS the
query's `$or`. The free-text search then wanted an `$or` of its own (user_id
∈ matched OR symbol regex) and assigned it over the top. A dict holds `$or`
once, so the demo exclusion was gone the moment an operator typed two
characters into the search box: DEMO accounts' orders showed up in the live
admin orders list, next to real-money rows, and nothing raised — the list
just got longer. The old comment claimed a "top-level merge" kept things
intact, which is true for sibling keys (`status`, `user_id`) and false for
the one key both clauses wanted.

The positions branch and the SL/TP branch in the same file already got this
right by splicing through `$and`; this test pins the orders branch to the
same rule, and pins the whole file against the assignment coming back.

    pytest -q backend/tests/test_orders_search_demo_leak.py
"""

from __future__ import annotations

import inspect
import re

from app.api.v1.admin import trading
from app.core.dependencies import merge_scope

NOT_DEMO = {"$or": [{"is_demo": {"$ne": True}}, {"is_demo": {"$exists": False}}]}
SEARCH = {
    "$or": [
        {"user_id": {"$in": ["u1"]}},
        {"instrument.symbol": {"$regex": "AJAY", "$options": "i"}},
    ]
}


def _orders_query(*, status=None, scope=None, search=None):
    """The shape the endpoint builds, in the same order it builds it."""
    query = dict(NOT_DEMO)
    if status:
        query["status"] = status
    if scope is not None:
        query["user_id"] = {"$in": scope}
    if search is not None:
        merge_scope(query, None, search)
    return query


def test_the_demo_exclusion_survives_a_search():
    """The bug, stated as the thing an operator saw: type in the box, demo
    rows appear. Both `$or`s have to reach Mongo."""
    q = _orders_query(search=SEARCH)

    assert q["$or"] == NOT_DEMO["$or"], "demo exclusion was overwritten by the search"
    assert q["$and"] == [SEARCH]


def test_status_and_scope_still_narrow_the_search():
    """Sibling keys were never the hazard, but they are what the operator
    filters on, so keep them pinned alongside the two `$or`s."""
    q = _orders_query(status={"$in": ["PENDING", "OPEN"]}, scope=["u1", "u2"], search=SEARCH)

    assert q["status"] == {"$in": ["PENDING", "OPEN"]}
    assert q["user_id"] == {"$in": ["u1", "u2"]}
    assert q["$or"] == NOT_DEMO["$or"]
    assert q["$and"] == [SEARCH]


def test_no_search_leaves_a_plain_indexed_query():
    """No `q` → no `$and` wrapper at all. merge_scope is only called on the
    search path, so the common load of the page is unchanged."""
    q = _orders_query(status="EXECUTED", scope=["u1"])

    assert "$and" not in q
    assert q == {**NOT_DEMO, "status": "EXECUTED", "user_id": {"$in": ["u1"]}}


def test_an_empty_match_set_still_returns_nothing_on_the_user_axis():
    """`q` that matches no user must not widen to the whole book: `$in: []`
    matches nothing and only the symbol regex can still hit."""
    empty = {"$or": [{"user_id": {"$in": []}}, {"instrument.symbol": {"$regex": "ZZZ"}}]}
    q = _orders_query(search=empty)

    assert q["$and"] == [empty]
    assert q["$or"] == NOT_DEMO["$or"]


def test_the_orders_endpoint_merges_instead_of_assigning():
    """Pin the call site. `query["$or"] = ` is the exact line that leaked."""
    src = inspect.getsource(trading.list_orders)

    assert "merge_scope(" in src
    assert 'query["$or"] =' not in src


def test_nothing_in_the_file_assigns_over_an_existing_or():
    """Root cause, not one line: there are ~10 `$or` clauses in this module.
    Any later `query[...]["$or"] = ` or `.update()` onto a dict that already
    carries one is the same silent-widening bug, so fail the whole file on
    the pattern rather than waiting for the next operator report."""
    src = inspect.getsource(trading)

    # Bare `<name>["$or"] = ...` — building a fresh literal is fine, mutating
    # a dict's `$or` by assignment is what dropped the demo filter.
    assert not re.search(r'^\s*\w+\["\$or"\]\s*=', src, re.M)
    # `.update(` on a query dict would do the same for any colliding key.
    # The one survivor is the WS payload builder, which is not a query.
    assert [m.group(1) for m in re.finditer(r"(\w+)\.update\(", src)] == ["payload"]
