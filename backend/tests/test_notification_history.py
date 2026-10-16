"""The history of what was sent to users, and who is on the hook for it.

The operator's ask: "jo jo notification send huye hai user ko uska history
dekhna hai — kya kya send hua, bulk me kon kon user ko kya send hua … and
ye superadmin admin and broker sab me show karega, jo jo user kiske ander
me hai."

`Notification` is ONE ROW PER RECIPIENT and a bulk send is N rows from a
single `insert_many`, so there is no batch id to group on. The composite
(second, title, message, level, source, sender) is what turns the rows
already in the collection back into sends — no migration, no new field.

Three things here fail invisibly if they break, which is why each is
pinned:

  * the `source` filter sits AFTER `$group`. Moved before it, the derived
    source does not exist yet and the filter matches nothing; moved after
    `$facet`, `total` would count ROWS and a 674-recipient broadcast would
    read as 674 sends.
  * `_SOURCE_EXPR` has to recognise the sends that predate `data.source`.
    Get it wrong and the whole screen reads "system" — which looks like a
    working screen.
  * the recipients endpoint re-derives its scope. Drop that and any admin
    reads another admin's recipient list by guessing a timestamp — a
    cross-tenant read that raises nothing.

Pure parts only: no Mongo, no Redis.

    pytest -q backend/tests/test_notification_history.py
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import textwrap
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.admin import notifications as api
from app.models.user import UserRole
from app.services.chart_level_service import notify_levels_changed
from app.services.notification_service import notify_payment_details_changed

SCOPE = {"user_id": {"$in": ["u1", "u2"]}}


def _stages(pipeline, name):
    """Indices of every stage with key `name`."""
    return [i for i, s in enumerate(pipeline) if name in s]


def _pipe(**kw):
    kw = {"source": None, "skip": 0, "limit": 20, **kw}
    return api._sent_pipeline(dict(SCOPE), **kw)


# ── grouping: one row per SEND, not per recipient ────────────────────
def test_a_send_is_identified_by_the_composite_not_by_a_batch_id():
    """674 rows written in one `insert_many` share all six of these."""
    key = _pipe()[_stages(_pipe(), "$group")[0]]["$group"]["_id"]

    assert set(key) == {"sec", "title", "message", "level", "source", "sender_id"}
    assert key["title"] == "$title"
    assert key["message"] == "$message"
    assert key["level"] == "$level"
    assert key["sender_id"] == {"$ifNull": ["$data.sender_id", None]}


def test_the_second_is_truncated_not_taken_whole():
    """Rows of one `insert_many` land milliseconds apart, so the raw
    `created_at` would split a single send into hundreds of groups."""
    sec = _pipe()[1]["$group"]["_id"]["sec"]

    assert sec == {
        "$dateToString": {"date": "$created_at", "format": "%Y-%m-%dT%H:%M:%S"}
    }
    assert "$dateTrunc" not in str(_pipe()), "same truncation, and no Mongo 5.0 floor"


def test_sent_at_is_a_real_timestamp_the_drilldown_can_re_bound():
    """The group key is a truncated STRING; `sent_at` has to come back as
    an actual date, because `/sent/recipients` parses it to find the send
    again."""
    group = _pipe()[1]["$group"]

    assert group["sent_at"] == {"$min": "$created_at"}


def test_recipients_counts_rows_and_read_count_only_the_read_ones():
    group = _pipe()[1]["$group"]

    assert group["recipients"] == {"$sum": 1}
    assert group["read_count"] == {"$sum": {"$cond": ["$is_read", 1, 0]}}


# ── pagination: the total is sends, not rows ─────────────────────────
def test_the_total_is_counted_after_the_group():
    """`$count` inside `$facet`, which runs on the GROUPED documents. Count
    the input instead and one broadcast reads as 674 separate sends."""
    p = _pipe()
    facet = p[_stages(p, "$facet")[0]]["$facet"]

    assert _stages(p, "$group")[0] < _stages(p, "$facet")[0]
    assert facet["total"] == [{"$count": "n"}]
    assert facet["items"] == [
        {"$sort": {"sent_at": -1}},
        {"$skip": 0},
        {"$limit": 20},
    ]


def test_the_page_window_is_the_one_asked_for():
    facet = _pipe(skip=40, limit=10)[-1]["$facet"]

    assert {"$skip": 40} in facet["items"]
    assert {"$limit": 10} in facet["items"]


def test_the_source_filter_runs_between_the_group_and_the_facet():
    """THE ordering regression. `source` is DERIVED into the group key, so
    before `$group` it does not exist (matches nothing) and after `$facet`
    it is too late to keep `total` honest."""
    p = _pipe(source="chart_lines")
    matches = _stages(p, "$match")

    assert p[matches[-1]] == {"$match": {"_id.source": "chart_lines"}}
    assert _stages(p, "$group")[0] < matches[-1] < _stages(p, "$facet")[0]


def test_no_source_filter_adds_no_stage():
    assert len(_pipe(source=None)) == len(_pipe(source="x")) - 1


def test_the_callers_scope_is_the_first_stage():
    """A `$match` that is not first still works but scans; more to the
    point, the scope must never be reachable past the group."""
    assert _pipe()[0] == {"$match": SCOPE}


# ── source derivation: the old sends must stay identifiable ──────────
def _derive(row: dict) -> str:
    """Evaluate `_SOURCE_EXPR` the way Mongo would.

    Fifteen lines of `$switch` beats standing up a Mongo container to
    learn whether a 2026 chart-line row still reads as `chart_lines`.
    """

    def ev(expr):
        if isinstance(expr, str) and expr.startswith("$"):
            cur = row
            for part in expr[1:].split("."):
                cur = cur.get(part) if isinstance(cur, dict) else None
            return cur
        if isinstance(expr, dict):
            if "$ifNull" in expr:
                a, b = expr["$ifNull"]
                return ev(a) if ev(a) is not None else ev(b)
            if "$eq" in expr:
                a, b = expr["$eq"]
                return ev(a) == ev(b)
        return expr

    switch = api._SOURCE_EXPR["$switch"]
    for branch in switch["branches"]:
        if ev(branch["case"]):
            return ev(branch["then"])
    return switch["default"]


def test_a_row_that_carries_its_own_source_is_taken_at_its_word():
    assert (
        _derive(
            {
                "title": "Important Update for Deposit",
                "data": {"source": "admin_broadcast", "sender_id": "a1"},
            }
        )
        == "admin_broadcast"
    )
    assert _derive({"title": "x", "data": {"source": "zerodha_auto_login"}}) == (
        "zerodha_auto_login"
    )


def test_the_chart_line_sends_that_predate_the_source_key_are_not_system():
    """The exact `data` the chart-line sender used to write. 90 days of
    these are in the collection right now and they are the sends the
    operator asked about first."""
    assert (
        _derive(
            {"title": "Chart lines updated", "data": {"link": "/terminal", "category": "general"}}
        )
        == "chart_lines"
    )


def test_the_payment_sends_that_predate_the_source_key_are_not_system():
    assert (
        _derive(
            {"title": "Deposit details updated", "data": {"link": "/wallet", "category": "payment"}}
        )
        == "payment_details"
    )


def test_anything_genuinely_unlabelled_falls_through_to_system():
    assert _derive({"title": "Order filled", "data": {}}) == "system"
    assert _derive({"title": "Order filled"}) == "system"
    assert _derive({"title": "x", "data": {"source": None}}) == "system"


def test_the_generic_category_alone_is_not_read_as_chart_lines():
    """`category: general` is the default tone, not a sender. Only the
    chart-line TITLE identifies that family in the old rows."""
    assert _derive({"title": "Welcome", "data": {"category": "general"}}) == "system"


# ── attribution: the two senders that used to be anonymous ───────────
def _row_data(fn) -> dict:
    """The `data=` dict literal handed to the `Notification(...)` this
    function builds — the row as the history will read it.

    Grepping the raw source instead is not enough: both senders ALSO put
    `category` into their WebSocket payload, so a `"category" in src`
    assertion passed with the one in the DB row deleted.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Notification"):
            continue
        for kw in node.keywords:
            if kw.arg == "data":
                out = {}
                for k, v in zip(kw.value.keys, kw.value.values, strict=True):
                    try:
                        out[ast.literal_eval(k)] = ast.literal_eval(v)
                    except ValueError:  # an expression, e.g. str(actor.id)
                        out[ast.literal_eval(k)] = ast.unparse(v)
                return out
    raise AssertionError(f"{fn.__name__} builds no Notification(data=...)")


@pytest.mark.parametrize(
    ("fn", "slug"),
    [(notify_payment_details_changed, "payment_details"), (notify_levels_changed, "chart_lines")],
)
def test_both_senders_now_stamp_who_sent_it(fn, slug):
    """A history that says "system" with nobody to ask is not worth
    opening. These are the two that wrote neither source nor sender."""
    data = _row_data(fn)

    assert data["source"] == slug
    assert data["sender_id"] == "str(actor.id)"


@pytest.mark.parametrize(
    ("fn", "category"),
    [(notify_payment_details_changed, "payment"), (notify_levels_changed, "general")],
)
def test_the_category_the_user_side_reads_for_the_sound_is_untouched(fn, category):
    """`category` picks the notification SOUND on the client. Renaming or
    dropping it while adding `source` would silently change what hundreds
    of users hear, with nothing to show it had happened."""
    assert _row_data(fn)["category"] == category


def _row_kwargs(fn) -> set[str]:
    """Keyword names on the `Notification(...)` call inside `fn`."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Notification":
            return {kw.arg for kw in node.keywords}
    raise AssertionError(f"{fn.__name__} builds no Notification(...)")


@pytest.mark.parametrize(
    "fn",
    [notify_payment_details_changed, notify_levels_changed, api.broadcast_notification],
)
def test_one_send_is_stamped_once_not_once_per_row(fn):
    """`created_at` defaults per ROW, and the rows of one send are built in
    a list comprehension that takes ~9 ms per 674 (~140 ms per 10 000). A
    send that starts late in a second therefore lands partly in the next
    one, and `/sent` — which groups BY that second — shows it twice with
    the recipients split between the halves. Measured incidence before the
    hoist: ~0.9% of 674-user sends, ~14% at 10 000. One stamp for the whole
    `insert_many` removes the boundary entirely."""
    assert "created_at" in _row_kwargs(fn), (
        f"{fn.__name__} lets every row stamp itself; a bulk send can then "
        "straddle a second boundary and be counted as two sends"
    )


@pytest.mark.parametrize("fn", [notify_payment_details_changed, notify_levels_changed])
def test_the_deep_link_survived_the_edit_too(fn):
    """`link` is what the bell row opens; it sits in the same dict."""
    assert _row_data(fn)["link"].startswith("/")


# ── scope: who sees whose sends ──────────────────────────────────────
def test_a_super_admin_sees_every_send_on_the_platform():
    """The deliberate exception. `scoped_user_ids` would answer the much
    narrower "my own DIRECT clients" (`_pool_clause` → `assigned_admin_id:
    None`), which is the wrong question for a screen whose entire purpose
    is the platform owner auditing what their ADMINS pushed out. Same
    exception `chart_level_service.notify_levels_changed` makes."""
    assert asyncio.run(api._sent_scope(SimpleNamespace(role=UserRole.SUPER_ADMIN))) == {}


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.BROKER, UserRole.EMPLOYEE])
def test_every_other_role_is_pinned_to_the_users_beneath_them(role, monkeypatch):
    """One resolver for all three — `scoped_user_ids` already walks the
    ADMIN broker-subtree union and resolves EMPLOYEE to its parent, so
    this view cannot drift from the broadcast it is the history of."""
    seen = {}

    async def fake(admin, *, include_closed=False):
        seen["include_closed"] = include_closed
        return ["u1", "u2"]

    monkeypatch.setattr(api, "scoped_user_ids", fake)
    scope = asyncio.run(api._sent_scope(SimpleNamespace(role=role)))

    assert scope == SCOPE
    assert seen["include_closed"] is True, (
        "a user closed AFTER a broadcast still received it; dropping them "
        "makes the recipient count drift from what was sent"
    )


def test_an_empty_pool_matches_nothing_rather_than_everything(monkeypatch):
    """Fails closed: `$in: []` matches no document. An actor with no users
    must not fall back to the unfiltered super-admin query."""

    async def fake(admin, *, include_closed=False):
        return []

    monkeypatch.setattr(api, "scoped_user_ids", fake)
    assert asyncio.run(api._sent_scope(SimpleNamespace(role=UserRole.BROKER))) == {
        "user_id": {"$in": []}
    }


def test_the_super_admin_branch_is_decided_before_the_pool_resolver_runs():
    src = inspect.getsource(api._sent_scope)
    assert "SUPER_ADMIN" in src[: src.index("scoped_user_ids")]


def test_both_views_resolve_their_scope_through_the_one_helper():
    """The drilldown is the dangerous one: it is addressed by a timestamp
    and a title, both guessable, so it has to re-apply the scope itself."""
    for fn in (api.sent_history, api.sent_recipients):
        assert "_sent_scope(admin)" in inspect.getsource(fn), fn.__name__


def test_the_search_box_cannot_evict_the_scope_clause():
    """The search is an `$or`. A dict holds `$or` once, so pasting it in
    beside a scope that is also an `$or` keeps one of the two — and when
    the one that goes is the SCOPE, nothing raises."""
    src = inspect.getsource(api.sent_history)
    assert "merge_scope(match, None," in src
    assert 'match["$or"]' not in src


# ── the drilldown is bounded to exactly one second ───────────────────
def test_the_send_is_bounded_to_the_second_it_names():
    src = inspect.getsource(api.sent_recipients)
    assert '"$gte": start, "$lt": start + timedelta(seconds=1)' in src
    assert "_one_second(sent_at)" in src


def test_a_stamp_with_milliseconds_lands_on_its_second():
    assert api._one_second("2026-10-15T10:12:47.380Z") == datetime(
        2026, 10, 15, 10, 12, 47, tzinfo=UTC
    )


def test_an_offset_is_converted_rather_than_trusted():
    """IST in, UTC out — the stored values are UTC."""
    assert api._one_second("2026-10-15T15:42:47.380+05:30") == datetime(
        2026, 10, 15, 10, 12, 47, tzinfo=UTC
    )


def test_a_naive_stamp_is_read_as_utc_not_as_server_local_time():
    """The Motor client is tz_aware, so a naive value compared against an
    aware one raises in Python and shifts by the host's zone in Mongo."""
    parsed = api._one_second("2026-10-15T10:12:47")
    assert parsed.tzinfo is not None
    assert parsed == datetime(2026, 10, 15, 10, 12, 47, tzinfo=UTC)


@pytest.mark.parametrize("bad", ["", "   ", "yesterday", "2026-13-01T00:00:00Z", "1760522567"])
def test_an_unparseable_stamp_is_a_400_and_never_an_open_range(bad):
    """Falling back to "no bound" would hand back every recipient of every
    send in scope under one title."""
    with pytest.raises(HTTPException) as e:
        api._one_second(bad)
    assert e.value.status_code == 400


# ── the recipient list stays inside the contact rules ────────────────
def test_the_recipient_list_carries_no_contacts():
    """Client email and mobile are masked from admins behind the
    `user_contacts` grant. A recipient list needs a name and a code, so it
    has no business re-exposing them through a side door."""
    body = inspect.getsource(api.sent_recipients).split('"""')[-1]  # code, not the docstring
    for leaked in ("email", "mobile", "phone", "contact_out", "contact_display"):
        assert leaked not in body, leaked


def test_both_views_need_the_same_permission_as_the_broadcast():
    """Reading what was sent is the same question as sending it."""
    for fn in (api.sent_history, api.sent_recipients, api.broadcast_notification):
        assert 'require_perm("users", "read")' in inspect.getsource(fn), fn.__name__
