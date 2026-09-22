"""User codes and optional contacts.

The code is a login id now, so its shape matters: six characters, never
all-digits (login tries mobile before user_code), and no O/0 or I/1/L to
misread off a screen.

    pytest -q backend/tests/test_user_identity.py
"""

from __future__ import annotations

import pytest

from app.services.user_service import (
    NO_EMAIL_DOMAIN,
    NO_MOBILE_PREFIX,
    email_or_mobile_taken,
    is_placeholder_contact,
    make_user_code,
)

AMBIGUOUS = set("O0I1L")


def test_code_shape():
    for _ in range(200):
        code = make_user_code()
        assert len(code) == 6
        assert code.isalnum() and code.isupper()
        assert not AMBIGUOUS & set(code), code
        # A letter AND a digit: all-digits would be read as a phone number
        # by the login lookup, all-letters is just the house style.
        assert any(c.isdigit() for c in code), code
        assert any(c.isalpha() for c in code), code


def test_codes_are_not_all_the_same():
    assert len({make_user_code() for _ in range(50)}) > 40


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (f"k7m2qx@{NO_EMAIL_DOMAIN}", True),
        (f"{NO_MOBILE_PREFIX}K7M2QX", True),
        ("ravi@gmail.com", False),
        ("9876543210", False),
        ("", False),
        (None, False),
    ],
)
def test_placeholder_detection(value, expected):
    assert is_placeholder_contact(value) is expected


@pytest.mark.asyncio
async def test_a_user_with_neither_contact_never_conflicts():
    """Two admin-created users with no email and no phone must both be
    allowed — the check has nothing to compare, so it must not fall
    through to a query that matches every placeholder row."""
    assert await email_or_mobile_taken("", "") is None
    assert await email_or_mobile_taken(None, None) is None
