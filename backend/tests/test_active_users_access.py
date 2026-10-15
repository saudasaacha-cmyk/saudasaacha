"""Who the Active Users roster may show, and whose contacts it may print.

Two grants decide that, and both used to be losable by accident:

  • `user_contacts` — `collect_rows` took `reveal_contacts=True` by
    default, so the ONE caller that forgot the kwarg would have printed
    every email and phone on the platform;
  • `active_users` with a scope — a caller-supplied `role` REPLACED the
    clients-only exclusion, so a granted ADMIN asking `?role=BROKER` got
    back the broker and employee logins that exclusion exists to hide.

Source- and signature-level, like test_presence.py: `_query` is pure, and
the leak is in a default argument — neither needs a database to prove.

    pytest -q backend/tests/test_active_users_access.py
"""

from __future__ import annotations

import inspect
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.admin import users as admin_users
from app.api.v1.admin.users import list_active_users
from app.models.user import UserRole
from app.services.active_users_service import _ADMIN_TIER_ROLES, _query, collect_rows
from app.utils.time_utils import UTC

_Q = {"q": None, "include_demo": True, "scope": None}


def _probe(role: UserRole | None = None):
    """Stands in for the two endpoints' `role` param — same annotation,
    none of their auth. Module level so the postponed annotation resolves
    the way it does in the router."""
    return {"role": role}


def test_a_forgotten_contacts_kwarg_masks_instead_of_leaking():
    """The default is the safe half of the grant. Both call sites pass it
    explicitly, which is exactly why a wrong default would stay invisible
    until the first caller that doesn't."""
    assert inspect.signature(collect_rows).parameters["reveal_contacts"].default is False


def test_every_call_site_still_decides_contacts_for_itself():
    """A masking default is not a licence to stop resolving the grant: the
    page and its download must agree with `user_contacts`, not with the
    default."""
    assert "reveal_contacts" in inspect.getsource(admin_users._resolve_active_users_access)
    for fn in (admin_users.list_active_users, admin_users.export_active_users):
        assert "**access" in inspect.getsource(fn)


def test_a_role_filter_cannot_widen_a_scoped_admins_roster():
    """`?role=BROKER` from a granted ADMIN: the exclusion survives, so the
    two clauses AND into "a BROKER that is not admin-tier" — nothing."""
    clause = _query(**_Q, role="BROKER", clients_only=True)["role"]
    assert clause["$nin"] == _ADMIN_TIER_ROLES
    assert clause["$eq"] == "BROKER"


def test_the_exclusion_holds_with_no_role_asked_for():
    assert _query(**_Q, role=None, clients_only=True)["role"] == {"$nin": _ADMIN_TIER_ROLES}


def test_the_platform_view_filters_on_exactly_what_was_asked():
    """The super admin's roster includes the admin-tier logins on purpose,
    so an unscoped call must not inherit the exclusion."""
    assert _query(**_Q, role="CLIENT", clients_only=False)["role"] == {"$eq": "CLIENT"}
    assert "role" not in _query(**_Q, role=None, clients_only=False)


def test_an_unknown_role_is_a_422_not_an_empty_page():
    """Typed as the enum so FastAPI rejects `?role=garbage` at the door —
    a free-form string returned zero rows and looked like an answer."""
    for fn in (admin_users.list_active_users, admin_users.export_active_users):
        assert str(inspect.signature(fn).parameters["role"].annotation) == "UserRole | None"

    # And that annotation really does mean 422 rather than a coerced value.
    app = FastAPI()
    app.get("/probe")(_probe)
    client = TestClient(app)
    assert client.get("/probe", params={"role": "garbage"}).status_code == 422
    assert client.get("/probe", params={"role": "CLIENT"}).status_code == 200


def test_online_only_is_filtered_by_mongo_not_in_python():
    """The page polls every 20 s and the export repeats the work: the ids
    presence already found belong in the query, not in a loop that first
    hydrates everybody."""
    oids = _query(**_Q, role=None, clients_only=False, online_ids=["x", "y"])["_id"]
    assert oids == {"$in": ["x", "y"]}
    # No second filter left behind to disagree with the query.
    assert "online_only and since is None" not in inspect.getsource(collect_rows)


def test_the_page_is_told_whether_contacts_are_real():
    """The client cannot work this out from `/me`: `can_read_contacts`
    also requires the PARENT admin to still hold the grant, so an
    employee whose own flag outlived their admin's revocation would
    otherwise be told the column is readable over masked rows."""
    src = inspect.getsource(list_active_users)
    assert '"contacts_revealed": bool(access["reveal_contacts"])' in src
    # Same source of truth the rows themselves are masked from.
    assert "reveal_contacts" in src


def test_the_24h_filter_is_about_login_not_activity():
    """Worth pinning because the column is easy to misread: this filters
    on `last_login_at`, so a trader who signed in on Monday and kept the
    tab open is active today and NOT in this list. The UI label says
    "Logged in" for that reason."""
    cutoff = datetime(2026, 10, 15, 0, 0, tzinfo=UTC)
    out = _query(
        q=None,
        role=None,
        include_demo=False,
        scope=None,
        clients_only=False,
        logged_in_since=cutoff,
    )
    assert out["last_login_at"] == {"$gte": cutoff}
    # Never-logged-in rows carry no `last_login_at`, and `$gte` drops
    # them — "never signed in" is not "signed in recently".
    assert "$exists" not in out["last_login_at"]

    # Off by default: the roster is every ACTIVE account unless asked.
    plain = _query(
        q=None,
        role=None,
        include_demo=False,
        scope=None,
        clients_only=False,
    )
    assert "last_login_at" not in plain


def test_the_recency_clause_survives_a_scope_that_is_an_or():
    """It is a plain key, so it must sit beside the scope rather than
    inside the `$and` — and the scope's `$or` must still be there. This
    is the merge the whole dedupe exists for."""
    scope = {"$or": [{"assigned_admin_id": "A1"}, {"broker_ancestry": "B1"}]}
    out = _query(
        q=None,
        role=None,
        include_demo=False,
        scope=scope,
        clients_only=True,
        logged_in_since=datetime(2026, 10, 15, tzinfo=UTC),
    )
    assert "last_login_at" in out
    assert any("$or" in c for c in out.get("$and", [])), out
