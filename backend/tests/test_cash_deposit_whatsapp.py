"""A second WhatsApp desk, for cash-deposit hand-offs only.

A cash deposit submitted without a receipt does not go to the admin
queue — it goes to WhatsApp carrying the amount, the place and the client
code. That is a payments question rather than a support one, and often a
different person, so it gets its own number.

Three things have to hold, and each is a way this could quietly break:

  * it resolves through the SAME cascade as the support number, so a
    broker can point their own clients' cash at their own desk;
  * it falls back to the support number when nobody in the chain sets
    one — which is the state every pool starts in, so without the
    fallback this feature would break cash deposits on the day it
    shipped;
  * the walk is one function taking a field name, not two copies. Two
    copies of a cascade is how `scoped_admin_filter` and
    `_admin_pool_clause` drifted apart.

    pytest -q backend/tests/test_cash_deposit_whatsapp.py
"""

from __future__ import annotations

import inspect

from app.api.v1.admin import support as admin_support
from app.api.v1.user import support as user_support
from app.models.user import User


def test_the_column_exists_and_is_separate():
    assert "cash_deposit_whatsapp" in User.model_fields
    assert "support_whatsapp" in User.model_fields
    # Unset by default — every pool starts out inheriting.
    assert User.model_fields["cash_deposit_whatsapp"].default is None


def test_one_cascade_walk_serves_both_numbers():
    """Parameterised by field rather than copied. The duplicate-cascade
    mistake is the most expensive one in this codebase's history."""
    sig = inspect.signature(user_support._resolve_whatsapp_for_user)
    assert "field" in sig.parameters
    assert sig.parameters["field"].default == "support_whatsapp"
    src = inspect.getsource(user_support._resolve_whatsapp_for_user)
    assert "getattr(cur, field" in src, "the walk hard-codes a column again"


def test_the_super_admin_fallback_covers_both():
    """The chain terminates at the first node with neither a broker nor an
    admin, which is every admin AND the super admin — the gap fixed in
    4ca7f39. It has to apply to the new column too."""
    sig = inspect.signature(user_support._super_admin_whatsapp)
    assert "field" in sig.parameters
    assert "getattr(su[0], field" in inspect.getsource(user_support._super_admin_whatsapp)


def test_cash_falls_back_to_support_and_not_the_other_way():
    """Order matters. Cash → support keeps every existing pool working;
    support → cash would silently send support enquiries to a payments
    desk nobody staffed for them."""
    src = inspect.getsource(user_support)
    i_cash = src.index('"cash_deposit_whatsapp")')
    i_fallback = src.index("cash = whatsapp")
    assert i_cash < i_fallback
    assert "whatsapp = cash" not in src


def test_both_numbers_ride_the_same_permission_gate():
    """Super admin, admin and broker each set their own — and a broker
    still needs the `support` grant, exactly as for the support number.
    One gate, so a broker cannot be blocked from one and allowed the
    other."""
    src = inspect.getsource(admin_support.set_my_support)
    assert "_support_can_edit(admin)" in src
    assert "cash_deposit_whatsapp" in src


def test_an_untouched_field_is_not_blanked():
    """`None` means the form did not send it; `""` means clear. Without
    that distinction, saving the support number alone would wipe the cash
    one."""
    field = admin_support.SupportPayload.model_fields["cash_deposit_whatsapp"]
    assert field.default is None
    src = inspect.getsource(admin_support.set_my_support)
    assert "if new_cash is not None" in src


def test_a_short_number_is_refused_for_both():
    """`buildWhatsappUrl` hides the button under 8 digits, so storing one
    means storing a value the app can never show."""
    src = inspect.getsource(admin_support.set_my_support)
    assert src.count("_check_number(") == 2
    assert "digits) < 8" in inspect.getsource(admin_support._check_number)
