"""The KYC inbox is not a side door around the `user_contacts` grant.

`admin/users.py` masks a client's email unless the actor was granted
contacts, but the KYC review queue used to serialise `user.email` raw — so
any admin who could open KYC read every submitter's real address regardless
of the grant. Same policy, two endpoints, one of them wasn't enforcing it.

The ID-proof fields are deliberately NOT masked: reading the uploaded
document against the typed number IS the review. This test pins that too,
so a later over-correction that blanks them trips here instead of in
production, where an admin would silently be unable to approve anything.

    pytest -q backend/tests/test_kyc_contact_masking.py
"""

from __future__ import annotations

import inspect
import types

from app.api.v1.admin import kyc as admin_kyc
from app.models.kyc import KycAddressProofType, KycIdProofType
from app.services.user_service import CONTACT_MASK, placeholder_email

# Stand-ins rather than real Beanie docs so the test needs no Mongo / Redis.
_SUB = types.SimpleNamespace(
    id="507f1f77bcf86cd799439011",
    user_id="507f1f77bcf86cd799439012",
    id_proof_type=KycIdProofType.PAN,
    id_proof_number="ABCDE1234F",
    id_proof_url="/uploads/kyc/u/1.jpg",
    address_proof_type=KycAddressProofType.UTILITY_BILL,
    address_proof_url="/uploads/kyc/u/2.jpg",
    address_text="12 MG Road, Raipur",
    status=types.SimpleNamespace(value="PENDING"),
    submitted_at=None,
    reviewed_at=None,
    reviewed_by=None,
    admin_remark=None,
    rejection_reason=None,
)


def _user(email: str):
    return types.SimpleNamespace(user_code="CL82066844", full_name="Suresh", email=email)


def test_the_kyc_row_masks_the_submitter_email_by_default():
    row = admin_kyc._serialise(_SUB, _user("suresh@gmail.com"))

    assert row["user_email"] == CONTACT_MASK
    # Nothing of the original leaks through — not the local part, not the host.
    assert "suresh" not in row["user_email"]
    assert "gmail" not in row["user_email"]


def test_a_granted_admin_still_gets_the_real_email():
    row = admin_kyc._serialise(_SUB, _user("suresh@gmail.com"), reveal=True)
    assert row["user_email"] == "suresh@gmail.com"


def test_a_placeholder_reads_as_absent_not_as_hidden():
    """ "Hidden" and "this account has no email" are different facts, and
    `contact_out` is the one place that call is made — so the KYC row says
    the same thing the users table does."""
    for reveal in (False, True):
        row = admin_kyc._serialise(_SUB, _user(placeholder_email("CL82066844")), reveal=reveal)
        assert row["user_email"] is None


def test_a_missing_user_row_does_not_explode():
    """`list_kyc` builds a map by user id; a submission whose account was
    hard-deleted lands here with user=None."""
    row = admin_kyc._serialise(_SUB, None)
    assert row["user_email"] is None
    assert row["user_code"] is None
    assert row["id"] == "507f1f77bcf86cd799439011"


def test_reveal_is_keyword_only_and_defaults_to_false():
    """Positional would let `_serialise(s, user, True)` read as a third
    unrelated flag, and a default of True is how this bug shipped: the
    serialiser must fail CLOSED when a caller forgets."""
    sig = inspect.signature(admin_kyc._serialise)
    assert sig.parameters["reveal"].default is False
    assert sig.parameters["reveal"].kind is inspect.Parameter.KEYWORD_ONLY


def test_every_caller_resolves_the_grant_instead_of_taking_the_default():
    """The default protects a forgetful caller, but silently masking an
    endpoint that SHOULD reveal is a bug too. All four call sites must ask
    `can_read_contacts` rather than ride the default."""
    src = inspect.getsource(admin_kyc)
    calls = [ln for ln in src.splitlines() if "_serialise(" in ln and "def _serialise" not in ln]
    assert len(calls) == 4, calls
    for ln in calls:
        assert "reveal=" in ln, ln
    assert src.count("can_read_contacts") == 4


def test_the_review_documents_stay_visible():
    """Masking these would make the screen useless — flagged for the lead
    rather than "fixed"."""
    row = admin_kyc._serialise(_SUB, _user("suresh@gmail.com"))

    assert row["id_proof_number"] == "ABCDE1234F"
    assert row["id_proof_url"] == "/uploads/kyc/u/1.jpg"
    assert row["address_proof_url"] == "/uploads/kyc/u/2.jpg"
    assert row["address_text"] == "12 MG Road, Raipur"


def test_the_row_carries_no_other_contact_column():
    """If a mobile (or any other User contact) is ever added to this payload
    it has to go through `contact_out` as well — this catches a raw one."""
    row = admin_kyc._serialise(_SUB, _user("suresh@gmail.com"))

    gated = {"user_email"}
    assert {k for k in row if "email" in k or "mobile" in k or "phone" in k} == gated
