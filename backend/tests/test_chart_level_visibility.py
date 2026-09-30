"""Who sees admin chart lines, and whose switch decides it.

The rule the operator asked for: a sub-admin or broker may turn the lines
off for THEIR users, and a sub-admin who has not touched the switch follows
the super admin. A sub-admin's "off" must never reach the super admin's own
users — that is the case worth pinning, because getting it backwards hides
the feature from everybody on the platform.

    pytest -q backend/tests/test_chart_level_visibility.py
"""

from __future__ import annotations

import types

import pytest
from beanie import PydanticObjectId

import app.services.chart_level_service as cl

SUPER = {"owner_admin_id": None, "owner_broker_id": None}
ADMIN_ID = PydanticObjectId()
BROKER_ID = PydanticObjectId()
ADMIN = {"owner_admin_id": ADMIN_ID, "owner_broker_id": None}
BROKER = {"owner_admin_id": None, "owner_broker_id": BROKER_ID}


def _user(*, admin=None, broker=None, ancestry=()):
    return types.SimpleNamespace(
        assigned_admin_id=admin, assigned_broker_id=broker, broker_ancestry=list(ancestry)
    )


@pytest.fixture
def rows(monkeypatch):
    """In-memory stand-in for the visibility collection: {owner filter: on}."""
    store: dict[tuple, bool] = {}

    async def fake(f):
        key = (f["owner_admin_id"], f["owner_broker_id"])
        if key not in store:
            return None
        enabled, locked = store[key]
        return types.SimpleNamespace(enabled=enabled, locked=locked)

    monkeypatch.setattr(cl, "_visibility_row", fake)

    def put(owner, enabled, locked=False):
        """`enabled=None` removes the row — that is what 'Default' does."""
        key = (owner["owner_admin_id"], owner["owner_broker_id"])
        if enabled is None:
            store.pop(key, None)
        else:
            store[key] = (enabled, locked)

    return put


# ── the cascade itself ───────────────────────────────────────────────
def test_lines_stop_at_the_assigned_admin():
    """A sub-admin's user must never be shown the PLATFORM's levels — same
    rule as company banks."""
    got = cl._owner_cascade(_user(admin=ADMIN_ID, broker=BROKER_ID), include_platform=False)
    assert got == [BROKER, ADMIN]


def test_visibility_falls_through_to_the_platform():
    """'The sub-admin didn't choose' has to mean 'whatever the super admin
    said', so this cascade has one more step than the levels one."""
    got = cl._owner_cascade(_user(admin=ADMIN_ID, broker=BROKER_ID), include_platform=True)
    assert got == [BROKER, ADMIN, SUPER]


def test_parent_brokers_come_tip_first():
    root, mid = PydanticObjectId(), PydanticObjectId()
    got = cl._owner_cascade(
        _user(admin=ADMIN_ID, broker=BROKER_ID, ancestry=[root, mid]),
        include_platform=False,
    )
    assert got == [
        BROKER,
        {"owner_admin_id": None, "owner_broker_id": mid},
        {"owner_admin_id": None, "owner_broker_id": root},
        ADMIN,
    ]


# ── the resolution ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_shown_when_nobody_has_decided(rows):
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID)) is True


@pytest.mark.asyncio
async def test_sub_admin_inherits_the_super_admin(rows):
    rows(SUPER, False)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID)) is False
    rows(SUPER, True)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID)) is True


@pytest.mark.asyncio
async def test_a_sub_admins_off_does_not_reach_the_super_admins_users(rows):
    """Super admin ON, sub-admin OFF: only the super admin's own users keep
    their lines. This is the case the operator spelled out."""
    rows(SUPER, True)
    rows(ADMIN, False)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID)) is False
    assert await cl.visibility_for_user(_user()) is True  # direct super-admin user


@pytest.mark.asyncio
async def test_the_nearest_decision_wins(rows):
    rows(SUPER, True)
    rows(ADMIN, False)
    rows(BROKER, True)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID, broker=BROKER_ID)) is True


@pytest.mark.asyncio
async def test_hidden_users_get_no_lines_and_no_trend(rows, monkeypatch):
    """The switch has to bite in resolve_for_user, not only in the UI —
    otherwise the API still hands the browser every level."""
    rows(SUPER, False)

    async def boom(*a, **k):  # the lookup must never be reached
        raise AssertionError("looked up levels for a user who can't see them")

    monkeypatch.setattr(cl.Instrument, "find_one", boom)
    assert await cl.resolve_for_user(_user(), "XAUUSD") == {"levels": [], "trend": None}


# ── the super admin's pin ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_a_pinned_sub_admin_cannot_be_undone_from_below(rows):
    """Super admin hides lines for one sub-admin's pool. A broker under that
    sub-admin turning their own switch on must NOT bring them back — the
    nearer row would otherwise win and the block would leak."""
    rows(SUPER, True)
    rows(ADMIN, False, locked=True)
    rows(BROKER, True)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID, broker=BROKER_ID)) is False
    # …and a different sub-admin's users are untouched.
    other = PydanticObjectId()
    assert await cl.visibility_for_user(_user(admin=other)) is True


@pytest.mark.asyncio
async def test_a_pin_on_the_broker_itself_is_nearer_and_wins(rows):
    """Both pins are the super admin's, so the more specific one applies."""
    rows(ADMIN, False, locked=True)
    rows(BROKER, True, locked=True)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID, broker=BROKER_ID)) is True


@pytest.mark.asyncio
async def test_releasing_the_pin_hands_control_back(rows):
    """'Default' deletes the row rather than storing a third value, so the
    tier goes back to following whoever is above it — and keeps following it
    when the super admin later changes their mind."""
    rows(SUPER, True)
    rows(ADMIN, False, locked=True)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID)) is False
    rows(ADMIN, None)  # released
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID)) is True
    rows(SUPER, False)
    assert await cl.visibility_for_user(_user(admin=ADMIN_ID)) is False
