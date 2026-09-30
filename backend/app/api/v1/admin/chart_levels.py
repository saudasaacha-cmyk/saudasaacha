"""Admin chart lines — Excel round-trip.

Download a template for a segment, type a price under each line column,
upload it back. Each line's colour and label are set once at the top of the
sheet and apply to every instrument. Single rows can also be edited in
place. Each price becomes a horizontal line on that instrument's chart for
the users under this admin.

Rows are owned per admin tier (super-admin / admin / broker), same cascade as
crypto configs and company banks.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.dependencies import CurrentAdmin
from app.schemas.common import APIResponse
from app.services import chart_level_service

router = APIRouter(prefix="/chart-levels", tags=["admin-chart-levels"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# 2 MB. A template for the largest segment is a few tens of KB; anything this
# size is not one of our sheets and shouldn't reach the parser.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


async def _check_segment(segment: str) -> str:
    """Validate against segments that actually have instruments, not the
    SegmentType enum — instruments carry FOREX and COMMODITIES, which the
    enum does not, and the enum lists many segments holding nothing."""
    known = {s["value"] for s in await chart_level_service.available_segments()}
    if segment not in known:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No instruments in segment '{segment}'.",
        )
    return segment


@router.get("/segments", response_model=APIResponse[list])
async def segments(admin: CurrentAdmin):
    """Segments the picker offers: only those holding instruments, labelled
    the way the Segment Settings page labels them, biggest first."""
    return APIResponse(data=await chart_level_service.available_segments())


@router.get("/template")
async def download_template(admin: CurrentAdmin, segment: str = Query(...)):
    """XLSX of every instrument in `segment`, pre-filled with what is already
    saved so an edit is a round-trip rather than a retype."""
    await _check_segment(segment)
    data = await chart_level_service.build_template(admin, segment)
    filename = f"chart-levels-{segment}.xlsx"
    return Response(
        content=data,
        media_type=XLSX_MIME,
        headers={
            # RFC 5987 form as well, so a segment name never breaks the header.
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


@router.post("/import", response_model=APIResponse[dict])
async def import_levels(admin: CurrentAdmin, file: UploadFile = File(...)):
    """Upload a filled template. Replaces each listed instrument's lines."""
    name = (file.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload the .xlsx template downloaded from this page.",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is larger than 2 MB — that isn't one of our templates.",
        )
    try:
        result = await chart_level_service.import_workbook(admin, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return APIResponse(data=result)


class VisibilityIn(BaseModel):
    # None = clear my own choice and follow the tier above. The three states
    # are on / off / not-chosen, and not-chosen is the ABSENCE of a row.
    enabled: bool | None = None


@router.get("/visibility", response_model=APIResponse[dict])
async def get_visibility(admin: CurrentAdmin):
    """Whether this actor's users see chart lines, and where that came from."""
    return APIResponse(data=await chart_level_service.get_visibility(admin))


@router.put("/visibility", response_model=APIResponse[dict])
async def set_visibility(body: VisibilityIn, admin: CurrentAdmin):
    return APIResponse(
        data=await chart_level_service.set_visibility(admin, body.enabled)
    )


@router.get("", response_model=APIResponse[list])
async def list_levels(admin: CurrentAdmin, segment: str | None = Query(default=None)):
    if segment:
        await _check_segment(segment)
    return APIResponse(data=await chart_level_service.list_for_admin(admin, segment))


@router.delete("/{token}", response_model=APIResponse[dict])
async def clear_levels(token: str, admin: CurrentAdmin):
    # Tokens are opaque ids; keep the route from becoming a path-traversal
    # shaped lookup even though Beanie would only ever do an equality match.
    if not re.fullmatch(r"[A-Za-z0-9_:.\-]{1,64}", token):
        raise HTTPException(status_code=400, detail="Invalid token.")
    removed = await chart_level_service.clear_for_admin(admin, token)
    return APIResponse(data={"cleared": removed})


class LevelIn(BaseModel):
    price: str | float | None = None
    color: str | None = None
    label: str | None = Field(default=None, max_length=40)


class LevelsIn(BaseModel):
    levels: list[LevelIn] = Field(default_factory=list, max_length=200)
    # Uptrend / Downtrend / Sideways. Anything else is dropped by the
    # service rather than stored, so the chart chip can't read as garbage.
    trend: str | None = Field(default=None, max_length=20)


@router.put("/{token}", response_model=APIResponse[dict])
async def save_levels(token: str, body: LevelsIn, admin: CurrentAdmin):
    """Replace one instrument's lines from the inline editor. An empty list
    clears them, same as an all-blank row in the sheet."""
    if not re.fullmatch(r"[A-Za-z0-9_:.\-]{1,64}", token):
        raise HTTPException(status_code=400, detail="Invalid token.")
    try:
        result = await chart_level_service.save_levels(
            admin, token, [lv.model_dump() for lv in body.levels], body.trend
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return APIResponse(data=result)
