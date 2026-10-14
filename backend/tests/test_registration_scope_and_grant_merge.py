"""Two settings that must land on the row that actually governs the behaviour.

  • The website-registration switch is read and written on the actor whose
    /register flow it gates. An employee owns no signup flow, so both the
    GET and the PUT resolve its parent admin first — otherwise an employee
    flipped a dead flag on its own row and got a success toast while the
    admin's signup page stayed open.
  • The all-sections backfill re-asserts; it never revokes. `active_users`
    and `user_contacts` are explicit super-admin decisions, so a re-run
    carries over whatever the row already holds instead of writing False.

    pytest -q backend/tests/test_registration_scope_and_grant_merge.py
"""

from __future__ import annotations

import inspect

from app.api.v1.admin.dashboard import (
    get_registration_status,
    set_registration_status,
)
from app.models.user import AdminPermissions
from scripts.grant_all_sections_to_existing_admins import SUPER_ADMIN_ONLY, _merged


def test_a_re_run_keeps_an_explicit_contacts_grant():
    """The regression: the sweep used to clobber the grant, closing contact
    access for the admin's brokers and employees too, with no audit row."""
    granted = AdminPermissions(user_contacts=True, active_users=True)
    merged = _merged(granted)
    assert merged.user_contacts is True
    assert merged.active_users is True


def test_a_re_run_does_not_hand_out_what_was_never_granted():
    """Preserving is not granting — a row that was denied stays denied."""
    merged = _merged(AdminPermissions())
    assert merged.user_contacts is False
    assert merged.active_users is False


def test_a_brand_new_admin_is_denied_by_default():
    """No permissions dict at all: nothing to preserve, so deny."""
    merged = _merged(None)
    assert all(getattr(merged, f) is False for f in SUPER_ADMIN_ONLY)


def test_every_other_section_is_still_granted():
    """That is the whole point of the backfill — only the two privacy
    sections are exempt."""
    merged = _merged(None)
    granted = {f for f in AdminPermissions.model_fields if getattr(merged, f)}
    assert granted == set(AdminPermissions.model_fields) - SUPER_ADMIN_ONLY


def test_the_backfill_is_idempotent():
    """Second pass over its own output changes nothing."""
    once = _merged(AdminPermissions(user_contacts=True))
    assert _merged(once).model_dump() == once.model_dump()


def test_the_registration_read_resolves_the_pool_owner():
    src = inspect.getsource(get_registration_status)
    assert "await effective_scope_actor(admin)" in src
    assert 'getattr(admin, "registration_enabled"' not in src


def test_the_registration_write_targets_the_pool_owner():
    """A save on `admin` is the bug: for an employee that is the employee."""
    src = inspect.getsource(set_registration_status)
    assert "await effective_scope_actor(admin)" in src
    assert "admin.registration_enabled" not in src
    assert "await admin.save()" not in src


def test_a_broker_is_refused_the_registration_switch():
    """Signup resolves the owner from `assigned_admin_id`, which is an
    ADMIN or the super admin — never a broker. The switch used to accept
    a broker's click and report success while signups stayed open."""
    import types

    import pytest

    from app.api.v1.admin.dashboard import _assert_owns_registration
    from app.models.user import UserRole

    with pytest.raises(Exception) as exc:
        _assert_owns_registration(types.SimpleNamespace(role=UserRole.BROKER))
    assert getattr(exc.value, "status_code", None) == 403

    # The roles that DO own a /register flow pass straight through.
    for role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        _assert_owns_registration(types.SimpleNamespace(role=role))


def test_the_broker_check_runs_on_the_resolved_actor():
    """An EMPLOYEE of a broker must be refused too — the check has to sit
    after `effective_scope_actor`, not on the caller."""
    import inspect

    from app.api.v1.admin import dashboard

    for fn in (dashboard.get_registration_status, dashboard.set_registration_status):
        src = inspect.getsource(fn)
        i_resolve = src.index("effective_scope_actor(admin)")
        i_check = src.index("_assert_owns_registration(actor)")
        assert i_resolve < i_check, fn.__name__
