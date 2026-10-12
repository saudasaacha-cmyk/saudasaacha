"""An admin editing an inherited script override forks it, not the original.

Admins are SHOWN the super-admin's platform rows so they can see what
they inherit. Being shown a setting you cannot change for your own users
is not useful — but letting the edit through to the platform row would
change it for every other admin's users too. So the first edit forks.

    pytest -q backend/tests/test_script_override_fork.py
"""

from __future__ import annotations

import inspect
import types

from beanie import PydanticObjectId

from app.api.v1.admin.netting import (
    _can_edit_script,
    _is_platform_script,
    _scope_for,
    update_script,
)
from app.models.user import UserRole

ADMIN_ID = PydanticObjectId()
OTHER_ADMIN_ID = PydanticObjectId()
BROKER_ID = PydanticObjectId()


def _actor(role, _id):
    return types.SimpleNamespace(role=role, id=_id)


def _row(admin_scope=None, broker_scope=None):
    return types.SimpleNamespace(
        scope_admin_id=admin_scope, scope_broker_id=broker_scope
    )


def test_a_platform_row_is_the_one_every_tier_inherits():
    assert _is_platform_script(_row()) is True
    assert _is_platform_script(_row(admin_scope=ADMIN_ID)) is False
    assert _is_platform_script(_row(broker_scope=BROKER_ID)) is False


def test_tiers_still_cannot_edit_each_other():
    """The fork is for INHERITED rows only. Another admin's row is not
    inherited — it stays off limits."""
    admin = _actor(UserRole.ADMIN, ADMIN_ID)
    assert _can_edit_script(admin, _row(admin_scope=ADMIN_ID)) is True
    assert _can_edit_script(admin, _row(admin_scope=OTHER_ADMIN_ID)) is False
    assert _can_edit_script(admin, _row(broker_scope=BROKER_ID)) is False
    # …and a platform row is still not directly editable — that is what
    # sends the request down the fork path instead.
    assert _can_edit_script(admin, _row()) is False


def test_super_admin_still_edits_the_platform_row_in_place():
    """Otherwise the platform default could never be changed at all."""
    sa = _actor(UserRole.SUPER_ADMIN, PydanticObjectId())
    assert _can_edit_script(sa, _row()) is True
    assert _can_edit_script(sa, _row(admin_scope=ADMIN_ID)) is True


def test_the_fork_is_stamped_with_the_callers_own_scope():
    admin = _actor(UserRole.ADMIN, ADMIN_ID)
    assert _scope_for(admin) == (ADMIN_ID, None)
    broker = _actor(UserRole.BROKER, BROKER_ID)
    assert _scope_for(broker) == (None, BROKER_ID)


def test_the_endpoint_forks_rather_than_refusing():
    src = inspect.getsource(update_script)
    assert "fork_script_for_scope" in src
    assert "_is_platform_script(existing)" in src
    # A row belonging to another tier must still be refused.
    assert "You can only edit script overrides scoped to your tier." in src


def test_the_fork_leaves_the_source_row_untouched():
    """The whole point: the super admin's row keeps applying to everyone
    else. The service must INSERT a new document, never save the source."""
    from app.services.netting_service import fork_script_for_scope

    src = inspect.getsource(fork_script_for_scope)
    assert "await doc.insert()" in src
    assert "src.save()" not in src
    # Inherited values are carried over, so forking changes only the
    # field the admin actually touched.
    assert "src.model_dump(" in src


def test_an_overridden_platform_row_is_hidden_from_that_tiers_list():
    """Both rows would otherwise be listed for the same symbol and read
    as duplicates, while only the tier's own one applies to its users."""
    from app.services.netting_service import list_scripts

    src = inspect.getsource(list_scripts)
    assert "not in own" in src


def test_each_pool_keeps_its_own_value():
    """The guarantee the operator asked for, in the resolver's own order.

    A user carries `assigned_admin_id`, so the admin-scoped row is only
    ever reached by that admin's own pool. A super-admin's direct user
    has no assigned_admin_id at all — that step is skipped and they fall
    through to the platform row the super admin set. Another admin's
    users have no row at their own scope, so they fall through too.
    """
    from app.services.netting_service import get_effective_settings

    src = inspect.getsource(get_effective_settings)
    exact = src.index("# Exact-match cascade")
    cascade = src[exact : exact + 600]
    # Broker, then admin, then platform — in that order, each only tried
    # when the more specific one found nothing.
    i_broker = cascade.index("_find_exact(None, _user_broker_id)")
    i_admin = cascade.index("_find_exact(_user_admin_id, None)")
    i_platform = cascade.index("_find_exact(None, None)")
    assert i_broker < i_admin < i_platform
    # The admin step is gated on the user actually having an admin, which
    # is what keeps a super-admin's direct users on the platform row.
    assert "_user_admin_id is not None" in cascade
