"""TeleCRM integration settings — single-row collection, super-admin only.

Credentials live here rather than in `.env` because the operator sets them
from the panel: the Async token is shown once by TeleCRM and pasted in, and
a `.env` edit would mean a deploy and a restart for something that is a
form field. Same shape as `ZerodhaSettings` for the same reason.

Tokens are returned to the UI as `"***"` with a separate `*_configured`
flag, and a write carrying `"***"` means "leave it alone" — the pattern
`zerodha_service` already uses, so a save that only toggles `enabled`
cannot blank a token by round-tripping a masked value.
"""

from __future__ import annotations

from datetime import datetime

from app.models._base import TimestampMixin


class TeleCrmSettings(TimestampMixin):
    # Nothing is sent while this is False. It is the default, so the
    # integration is inert until someone deliberately turns it on.
    enabled: bool = False

    enterprise_id: str = ""
    # Async-typed token: the Sync one returns 403 NOT_AUTHORIZED on the
    # ingestion endpoint, which is the single most likely setup mistake.
    async_token: str = ""
    # Optional, and only for verification. The Sync API's `POST /lead`
    # answers with a `remarks` array naming every field it IGNORED and why;
    # the Async endpoint drops them silently and still returns 200. Without
    # a Sync token a misspelled field name is invisible.
    sync_token: str = ""

    # Whether to set the CRM's `assignee` to the owning broker/admin.
    #
    # Off by default, and when on it is sent ONLY when ownership changes on
    # our side — never on a routine reconcile. TeleCRM's own caution: a
    # nightly job that re-asserts `assignee` overwrites whatever a human
    # did inside the CRM that day. Our platform is the source of truth for
    # WHO owns a client; it is not the source of truth for who is working
    # the lead today.
    send_assignee: bool = False

    # Status, for the panel. Not load-bearing.
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_message: str = ""

    last_push_at: datetime | None = None
    pushed_total: int = 0
    failed_total: int = 0
    last_error: str = ""

    class Settings:
        name = "telecrm_settings"
