"""Cash deposits, and the proof an admin attaches to a withdrawal.

A cash deposit rides the SAME request → admin approval → wallet credit
path as every other mode; it is a `PaymentMode`, not a second flow. What
makes it different is what counts as evidence: there is no UTR and no
company bank row to reconcile against, so the uploaded slip plus WHERE
the money changed hands is the entire audit trail. That is why city and
area are required rather than optional — a cash row without them is one
nobody can follow up on when it is disputed.

The withdrawal half runs the other way: the ADMIN uploads a file and the
USER sees it. "Paid" with nothing to show is what generates the next
support ticket.

    pytest -q backend/tests/test_cash_deposit_and_proof.py
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.admin import payin_out
from app.api.v1.user import wallet
from app.api.v1.user.wallet import ALLOWED_EXTS, _check_deposit_proof
from app.models.transaction import DepositRequest, PaymentMode, WithdrawalRequest


def _payload(**kw):
    base = {
        "payment_mode": "CASH",
        "screenshot_url": "/uploads/screenshots/u/abc.png",
        "crypto_tx_hash": None,
        "cash_city": "Indore",
        "cash_area": "Vijay Nagar",
    }
    base.update(kw)
    return SimpleNamespace(**base)


# ── cash is a payment mode, not a new flow ───────────────────────────
def test_cash_is_a_payment_mode():
    assert PaymentMode.CASH.value == "CASH"


def test_a_cash_deposit_carries_where_it_changed_hands():
    for field in ("cash_city", "cash_area"):
        assert field in DepositRequest.model_fields, field


# ── what counts as proof, per mode ───────────────────────────────────
def test_a_complete_cash_deposit_passes():
    assert _check_deposit_proof(_payload()) == (False, True)


@pytest.mark.parametrize("missing", ["cash_city", "cash_area"])
def test_a_cash_deposit_without_a_place_is_refused(missing):
    """Not stored-and-flagged — refused. There is no UTR to fall back on,
    so a cash row without a place is unanswerable from the moment it is
    written."""
    with pytest.raises(HTTPException) as e:
        _check_deposit_proof(_payload(**{missing: ""}))
    assert e.value.status_code == 400
    assert "city and area" in str(e.value.detail).lower()


def test_whitespace_is_not_a_place():
    with pytest.raises(HTTPException):
        _check_deposit_proof(_payload(cash_city="   "))


def test_a_cash_deposit_still_needs_the_slip():
    """The screenshot requirement is not relaxed for cash — it is the only
    document in the whole transaction."""
    with pytest.raises(HTTPException) as e:
        _check_deposit_proof(_payload(screenshot_url=""))
    assert "screenshot" in str(e.value.detail).lower()


def test_the_other_modes_are_unchanged():
    """The operator was explicit that the bank path is fine as it is."""
    bank = _payload(payment_mode="UPI", cash_city=None, cash_area=None)
    assert _check_deposit_proof(bank) == (False, False)
    # ...and crypto still takes the tx hash INSTEAD of a screenshot.
    crypto = _payload(
        payment_mode="CRYPTO", screenshot_url="", crypto_tx_hash="0xabc",
        cash_city=None, cash_area=None,
    )
    assert _check_deposit_proof(crypto) == (True, False)


def test_a_bank_deposit_is_not_asked_for_a_city():
    """Only the cash arm demands a place. Requiring it everywhere would
    break the mode the operator asked us to leave alone."""
    assert _check_deposit_proof(
        _payload(payment_mode="BANK_TRANSFER", cash_city=None, cash_area=None)
    ) == (False, False)


# ── the withdrawal proof ─────────────────────────────────────────────
def test_a_withdrawal_can_carry_an_admin_uploaded_proof():
    assert "proof_url" in WithdrawalRequest.model_fields


def test_the_proof_upload_is_scope_checked():
    """An admin must not be able to write a file onto another admin's
    user's row by guessing an id — the same gate every other withdrawal
    action goes through."""
    src = inspect.getsource(payin_out.upload_withdrawal_proof)
    assert "assert_user_in_scope" in src
    assert "require_perm" in src


def test_the_proof_accepts_a_pdf_where_the_user_upload_does_not():
    """A bank's own payment advice usually arrives as a PDF, and telling
    an admin to screenshot one to prove a payment is busywork. The user's
    own upload stays images-only."""
    assert ".pdf" in payin_out.PROOF_EXTS
    assert ".pdf" not in ALLOWED_EXTS


def test_the_proof_is_size_capped_and_written_off_the_event_loop():
    src = inspect.getsource(payin_out.upload_withdrawal_proof)
    assert "PROOF_MAX_BYTES" in src
    assert "to_thread" in src, "a sync write blocks every other request on this worker"


def test_the_user_sees_the_proof():
    """Storing it is pointless if it never reaches the person waiting for
    their money."""
    assert '"proof_url": r.proof_url' in inspect.getsource(wallet)
