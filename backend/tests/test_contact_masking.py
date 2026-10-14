"""A client's email and phone are not an admin's to read.

Not a broker's, not a sub-admin's, not the super admin's. The admin API
sends a mask instead of the value, so the real one never reaches a browser —
searching still runs against the real column on the server, so an admin who
already knows a number can still find the account.

    pytest -q backend/tests/test_contact_masking.py
"""

from __future__ import annotations

from app.models.user import UserRole, UserStatus
from app.services.user_service import (
    CONTACT_MASK,
    is_placeholder_contact,
    masked_contact,
    placeholder_email,
    placeholder_mobile,
)


def test_a_real_contact_never_comes_back():
    assert masked_contact("suresh@gmail.com") == CONTACT_MASK
    assert masked_contact("9999999995") == CONTACT_MASK
    # Nothing of the original survives in the mask.
    assert "9999" not in masked_contact("9999999995")
    assert "gmail" not in masked_contact("suresh@gmail.com")


def test_a_placeholder_reads_as_absent():
    """"Set but hidden" and "never filled in" are different facts: the mask
    says the first, None renders as a dash and says the second."""
    assert masked_contact(placeholder_email("CL82066844")) is None
    assert masked_contact(placeholder_mobile("CL82066844")) is None
    assert masked_contact(None) is None
    assert masked_contact("") is None
    assert is_placeholder_contact(placeholder_email("68GFP4"))


def test_the_admin_serializer_masks_both_columns():
    """The one serializer behind the users list, the user detail page and
    every mutation response.

    Asserted on BEHAVIOUR, not on the source containing a function name.
    The earlier version grepped for `masked_contact(u.email)` and went red
    the moment that call became `contact_out(u.email, reveal=...)` — a
    rename, not a regression. A test that cannot tell those apart costs
    more than it protects.
    """
    import types

    from app.api.v1.admin import users as admin_users

    # Every attribute `_ser` reads. A stand-in rather than a real User so
    # the test needs no Beanie init or Mongo.
    u = types.SimpleNamespace(
        id="507f1f77bcf86cd799439011",
        user_code="ABC123",
        full_name="Test",
        email="real@example.com",
        mobile="9876543210",
        role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        parent_id=None,
        assigned_admin_id=None,
        assigned_broker_id=None,
        last_transferred_at=None,
        last_transferred_by=None,
        last_login_at=None,
        created_at=None,
        two_fa_enabled=False,
        is_demo=False,
    )

    masked = admin_users._ser(u)
    assert masked["email"] == CONTACT_MASK
    assert masked["mobile"] == CONTACT_MASK

    revealed = admin_users._ser(u, reveal=True)
    assert revealed["email"] == "real@example.com"
    assert revealed["mobile"] == "9876543210"


def test_the_serializer_hides_contacts_unless_asked():
    """`reveal` defaults to False, so a caller that forgets the kwarg
    masks rather than leaks — the same rule the active-users service
    follows."""
    import inspect

    from app.api.v1.admin import users as admin_users

    sig = inspect.signature(admin_users._ser)
    assert sig.parameters["reveal"].default is False
