"""A client's email and phone are not an admin's to read.

Not a broker's, not a sub-admin's, not the super admin's. The admin API
sends a mask instead of the value, so the real one never reaches a browser —
searching still runs against the real column on the server, so an admin who
already knows a number can still find the account.

    pytest -q backend/tests/test_contact_masking.py
"""

from __future__ import annotations

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
    every mutation response."""
    import inspect

    from app.api.v1.admin import users as admin_users

    src = inspect.getsource(admin_users._ser)
    assert "masked_contact(u.email)" in src
    assert "masked_contact(u.mobile)" in src
    assert "u.email," not in src.replace("masked_contact(u.email),", "")
