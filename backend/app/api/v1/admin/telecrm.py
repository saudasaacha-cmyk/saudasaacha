"""TeleCRM integration — super admin only.

`SuperAdmin`, not `require_perm`: this is one set of platform credentials
and one outbound feed of every client's name and phone. It is not a
per-tenant setting and an admin has no business holding the token.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import SuperAdmin
from app.schemas.common import APIResponse
from app.services import telecrm_service as svc
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telecrm", tags=["admin-telecrm"])

MASK = "***"


def _out(s: Any) -> dict[str, Any]:
    """Never return a token. `*_configured` is what the UI needs to know,
    and `MASK` round-trips as "unchanged" on save."""
    return {
        "enabled": s.enabled,
        "enterprise_id": s.enterprise_id,
        "async_token": MASK if s.async_token else "",
        "async_token_configured": bool(s.async_token),
        "sync_token": MASK if s.sync_token else "",
        "sync_token_configured": bool(s.sync_token),
        "send_assignee": s.send_assignee,
        "last_test_at": s.last_test_at,
        "last_test_ok": s.last_test_ok,
        "last_test_message": s.last_test_message,
        "last_push_at": s.last_push_at,
        "pushed_total": s.pushed_total,
        "failed_total": s.failed_total,
        "last_error": s.last_error,
    }


class SettingsIn(BaseModel):
    enabled: bool | None = None
    enterprise_id: str | None = Field(default=None, max_length=120)
    async_token: str | None = Field(default=None, max_length=4000)
    sync_token: str | None = Field(default=None, max_length=4000)
    send_assignee: bool | None = None


@router.get("", response_model=APIResponse[dict])
async def get_settings(admin: SuperAdmin):
    return APIResponse(data=_out(await svc.get_settings()))


@router.put("", response_model=APIResponse[dict])
async def save_settings(body: SettingsIn, admin: SuperAdmin):
    """Partial save. A field left out is unchanged, and a token sent back
    as `***` is unchanged — otherwise toggling `enabled` from a form that
    round-trips the masked value would wipe the credentials."""
    s = await svc.get_settings()
    if body.enabled is not None:
        s.enabled = body.enabled
    if body.enterprise_id is not None:
        s.enterprise_id = body.enterprise_id.strip()
    if body.send_assignee is not None:
        s.send_assignee = body.send_assignee
    for attr, value in (("async_token", body.async_token), ("sync_token", body.sync_token)):
        if value is None:
            continue
        value = value.strip()
        if value == MASK:
            continue
        setattr(s, attr, value)
    await s.save()
    logger.info("telecrm_settings_saved by=%s enabled=%s", admin.user_code, s.enabled)
    return APIResponse(data=_out(s), message="Saved.")


@router.post("/test", response_model=APIResponse[dict])
async def test(admin: SuperAdmin):
    ok, message = await svc.test_connection()
    s = await svc.get_settings()
    s.last_test_at = now_utc()
    s.last_test_ok = ok
    s.last_test_message = message[:300]
    await s.save()
    return APIResponse(data=_out(s), message=message)


@router.post("/sync-all", response_model=APIResponse[dict])
async def sync_all(admin: SuperAdmin):
    """Kick off a full push of every sendable client.

    Fire-and-forget: ~680 leads at TeleCRM's ~5/sec ceiling is two to four
    minutes, which is far past any sane HTTP timeout. Progress shows up in
    the counters on this page.
    """
    if await svc.is_live() is None:
        return APIResponse(
            data={"started": False},
            message="Set an enterprise ID and an Async token, and enable the integration first.",
        )
    task = asyncio.create_task(svc.sync_all())
    _RUNS.add(task)
    task.add_done_callback(_RUNS.discard)
    logger.info("telecrm_sync_all_started by=%s", admin.user_code)
    return APIResponse(data={"started": True}, message="Sync started — counters update as it runs.")


_RUNS: set[asyncio.Task] = set()
