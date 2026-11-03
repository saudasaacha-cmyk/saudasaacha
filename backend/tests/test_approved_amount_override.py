"""An admin approving a different figure than the user asked for.

Two things have to hold and neither is obvious from the endpoint:

  * `amount` always means the money that actually moved. Every aggregation in
    the platform sums it, so it cannot become "what was requested" the moment
    an admin edits one row. `requested_amount` carries the other half, and it
    is set ONLY when the two differ — an untouched approval has to serialise
    exactly as it did before this field existed, or every reader has to learn
    a new shape for the ordinary case.

  * the override rides inside the same compare-and-set as the status. A
    double-clicked approve already fires two requests that both passed the
    read-time PENDING check; if the amount were written separately the row
    could record one figure while the wallet moved another.

    pytest -q backend/tests/test_approved_amount_override.py
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.admin.payin_out import (
    _apply_amount_override,
    _resolve_approved_amount,
)

ASKED = Decimal("50000.00")


# ── when nothing was overridden ──────────────────────────────────────
@pytest.mark.parametrize("raw", [None, "", "   "])
def test_an_untouched_approval_moves_the_requested_amount(raw):
    assert _resolve_approved_amount(raw, ASKED) == (ASKED, None)


def test_typing_the_same_figure_back_is_not_an_override():
    """Otherwise a row grows a `requested_amount` equal to its own amount, and
    every screen starts showing 'requested 50,000, approved 50,000'."""
    assert _resolve_approved_amount("50000", ASKED) == (ASKED, None)
    assert _resolve_approved_amount("50000.00", ASKED) == (ASKED, None)
    assert _resolve_approved_amount(50000.0, ASKED) == (ASKED, None)


def test_nothing_overridden_adds_no_claim_fields():
    row = SimpleNamespace(amount="untouched", requested_amount="untouched")
    assert _apply_amount_override(row, ASKED, None) == {}
    assert row.amount == "untouched"
    assert row.requested_amount == "untouched"


# ── when it was ──────────────────────────────────────────────────────
def test_approving_less_keeps_what_was_asked_for():
    amount, original = _resolve_approved_amount("45000", ASKED)
    assert amount == Decimal("45000.00")
    assert original == ASKED


def test_approving_more_is_allowed_and_also_recorded():
    amount, original = _resolve_approved_amount("55000", ASKED)
    assert amount == Decimal("55000.00")
    assert original == ASKED


def test_the_override_lands_on_the_row_and_in_the_claim():
    """Both halves from one call, because doing them separately is two
    chances to do only one."""
    row = SimpleNamespace(amount=None, requested_amount=None)
    fields = _apply_amount_override(row, Decimal("45000.00"), ASKED)
    assert set(fields) == {"amount", "requested_amount"}
    assert str(fields["amount"]) == "45000.00"
    assert str(fields["requested_amount"]) == "50000.00"
    # the in-memory row agrees with what will be stored
    assert fields["amount"] == row.amount
    assert fields["requested_amount"] == row.requested_amount


def test_paise_survive_the_round_trip():
    amount, original = _resolve_approved_amount("49999.99", ASKED)
    assert amount == Decimal("49999.99")
    assert original == ASKED


# ── what must be refused ─────────────────────────────────────────────
@pytest.mark.parametrize("bad", ["0", "-1", "-50000"])
def test_zero_or_negative_is_refused(bad):
    with pytest.raises(HTTPException) as e:
        _resolve_approved_amount(bad, ASKED)
    assert e.value.status_code == 400


@pytest.mark.parametrize("bad", ["abc", "50,000", "5e", "₹5000"])
def test_a_non_number_is_refused_rather_than_treated_as_blank(bad):
    """Blank means 'approve what was asked'. Letting a typo fall through to
    that would credit the original amount while the admin believed they had
    changed it."""
    with pytest.raises(HTTPException) as e:
        _resolve_approved_amount(bad, ASKED)
    assert e.value.status_code == 400


def test_an_extra_keystroke_is_caught():
    """50,000 -> 50,000,000 is one key. The ceiling is a typo guard, not a
    policy — real limits live in the deposit rules and, for a withdrawal, in
    the balance check this figure still has to clear."""
    with pytest.raises(HTTPException):
        _resolve_approved_amount("50000000000", ASKED)


def test_just_under_the_ceiling_is_still_allowed():
    amount, original = _resolve_approved_amount("999999999", ASKED)
    assert amount == Decimal("999999999.00")
    assert original == ASKED
