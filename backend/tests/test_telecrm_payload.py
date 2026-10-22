"""What we are allowed to send TeleCRM, and in what shape.

Every rule here is one TeleCRM drops SILENTLY — the ingestion endpoint
answers 200 and simply does not store the field, so a mistake in any of
them is invisible until someone opens the CRM and finds a column empty:

  * the lead identifier is `phone`, and a lead without one is dropped
    while still returning 200. A number we cannot build is a lead we must
    not send at all;
  * dates must be epoch MILLISECONDS as a JSON number. ISO 8601 is not
    parsed and "may be silently dropped or stored incorrectly";
  * field API names are case-sensitive and must already exist in the
    workspace — `User_Code` is dropped where `user_code` lands;
  * dropdowns auto-create an option on an unmatched value instead of
    failing, so loose casing quietly grows the option list rather than
    erroring.

Pure functions only — no Mongo, no Redis, no network.

    pytest -q backend/tests/test_telecrm_payload.py
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from types import SimpleNamespace

from app.models.telecrm_settings import TeleCrmSettings
from app.models.user import UserRole
from app.services import telecrm_service as svc
from app.services.user_service import placeholder_mobile


# ── the lead identifier ──────────────────────────────────────────────
def test_a_ten_digit_indian_number_gets_the_country_code():
    assert svc.to_phone("9876543210") == "919876543210"
    assert svc.to_phone(" 98765 43210 ") == "919876543210"
    assert svc.to_phone("+91 98765 43210") == "919876543210"
    assert svc.to_phone("919876543210") == "919876543210"


def test_a_number_we_cannot_build_is_not_sent_at_all():
    """Not "sent and hoped for" — a payload with no identifier is dropped
    by TeleCRM behind a 200, so it would look like a success forever."""
    for bad in (None, "", "   ", "99999", "12345678901234", "abcdefghij"):
        assert svc.to_phone(bad) is None, bad


def test_a_placeholder_contact_is_not_a_phone_number():
    """`+000<user_code>`-shaped stand-ins mean "no phone on file". Sending
    one would plant a junk lead that can never be matched or merged."""
    assert svc.to_phone(placeholder_mobile("CL82066844")) is None


# ── dates ────────────────────────────────────────────────────────────
def test_dates_go_as_epoch_milliseconds_not_iso():
    dt = datetime(2026, 10, 22, 9, 30, tzinfo=UTC)
    out = svc._ms(dt)
    assert out == int(dt.timestamp() * 1000)
    assert isinstance(out, int) and not isinstance(out, bool)
    # A string would be accepted by json.dumps and dropped by TeleCRM.
    assert not isinstance(out, str)
    assert svc._ms(None) is None


# ── owner labels ─────────────────────────────────────────────────────
def test_owner_type_distinguishes_a_sub_broker():
    user = SimpleNamespace()
    top = SimpleNamespace(assigned_broker_id=None)
    sub = SimpleNamespace(assigned_broker_id="B1")
    assert svc._owner_type(user, None) == "Admin"
    assert svc._owner_type(user, top) == "Broker"
    assert svc._owner_type(user, sub) == "Sub-broker"


def test_the_owner_type_values_match_the_dropdown_exactly():
    """An unmatched dropdown value does not error — TeleCRM auto-creates a
    new option. So "sub-broker" and "Sub-broker" would quietly become two
    options and split every report built on them."""
    allowed = {"Admin", "Broker", "Sub-broker"}
    for broker in (None, SimpleNamespace(assigned_broker_id=None), SimpleNamespace(assigned_broker_id="B")):
        assert svc._owner_type(SimpleNamespace(), broker) in allowed


# ── who becomes a lead ───────────────────────────────────────────────
def test_only_trading_roles_become_leads():
    """Staff are not leads. The operator was explicit: an admin's or
    broker's own account must not appear in a sales CRM — their clients do,
    carrying the owner as a field."""
    assert {UserRole.CLIENT, UserRole.DEALER, UserRole.MASTER} == svc.LEAD_ROLES
    for staff in (UserRole.ADMIN, UserRole.BROKER, UserRole.EMPLOYEE, UserRole.SUPER_ADMIN):
        assert staff not in svc.LEAD_ROLES


def test_push_user_checks_the_role_and_the_demo_flag():
    src = inspect.getsource(svc.push_user)
    assert "LEAD_ROLES" in src
    assert "is_demo" in src


# ── the rules that keep it safe to run against a live CRM ────────────
def test_nothing_is_sent_until_it_is_configured_and_enabled():
    """`enabled` defaults False and `is_live` demands both credentials, so
    a half-filled form cannot start pushing 680 people's names and phone
    numbers to a third party."""
    assert TeleCrmSettings.model_fields["enabled"].default is False
    src = inspect.getsource(svc.is_live)
    for need in ("enabled", "enterprise_id", "async_token"):
        assert need in src, need


def test_one_lead_is_never_written_twice_at_once():
    """TeleCRM asks that two requests for the same identifier never
    overlap. Four gunicorn workers make that a Redis problem, not an
    asyncio one."""
    src = inspect.getsource(svc._send)
    assert "nx=True" in src, "the per-lead lock must be set-if-absent"
    assert "telecrm:lead:" in src


def test_the_pace_gate_is_shared_across_workers():
    """One token's 18,000/hour is shared by every worker, so an in-process
    semaphore would only ever see a quarter of the traffic."""
    src = inspect.getsource(svc._pace)
    assert "incr" in src.lower()
    assert svc._MAX_PER_SEC <= 5, "TeleCRM's published ceiling is 5/sec"


def test_a_429_is_retried_and_a_403_is_not():
    """429 is "back off and retry" and create-or-update is idempotent. 403
    means the token is the wrong TYPE — retrying that forever would just
    bury the one error worth showing the operator."""
    src = inspect.getsource(svc._send)
    assert "429" in src and "sleep" in src
    assert "403" in src and "Async token" in src


def test_push_user_never_raises_into_a_login():
    """It is called from the login and registration handlers. A CRM outage
    must not cost anyone their session."""
    src = inspect.getsource(svc.push_user)
    assert "except Exception" in src
    assert "return False" in src


def test_the_background_task_is_held_until_it_finishes():
    """`create_task` keeps only a weak reference, so an unreferenced task
    can be collected mid-flight and the push would silently stop."""
    src = inspect.getsource(svc.push_user_bg)
    assert "add_done_callback" in src


def test_the_connection_test_does_not_write_a_lead():
    """The Async endpoint's only "test" is to create a lead. A connection
    test that leaves a real row in someone's CRM is not one they will press
    twice, so this uses the Sync API's read-only metadata call."""
    src = inspect.getsource(svc.test_connection)
    assert "metadata" in src
    assert "autoupdatelead" not in src
