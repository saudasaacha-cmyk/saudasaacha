"""Admin notifications — the bell IN, the broadcast OUT, the history of both.

Two collections, two different ACLs, which is why they share a file:

* `admin_notifications` (`AdminNotification`) is the bell. Every row is
  scoped to a single recipient admin, so those endpoints filter by
  ``recipient_admin_id = current_admin.id`` — no ACL plumbing beyond the
  standard `CurrentAdmin` dependency.
* `notifications` (`Notification`) is what went out to USERS. The
  broadcast writes it and `/sent` reads it back, both scoped through
  `scoped_user_ids` so an admin only ever sees their own pool's rows.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.dependencies import (
    CurrentAdmin,
    merge_scope,
    require_perm,
    scoped_user_ids,
)
from app.models.audit_log import AuditAction
from app.models.notification import (
    AdminNotification,
    Notification,
    NotificationLevel,
    NotificationType,
)
from app.models.user import User, UserRole
from app.schemas.common import APIResponse
from app.services.audit_service import log_event
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["admin-notifications"])


def _serialise(n: AdminNotification) -> dict[str, Any]:
    return {
        "id": str(n.id),
        "event_type": n.event_type.value,
        "level": n.level.value,
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "reference_type": n.reference_type,
        "reference_id": n.reference_id,
        "data": n.data,
        "is_read": n.is_read,
        "read_at": n.read_at,
        "created_at": n.created_at,
        "source_user_id": str(n.source_user_id),
    }


@router.get("", response_model=APIResponse[list])
async def list_notifications(
    admin: CurrentAdmin,
    only_unread: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Bell-panel feed. Defaults to "everything in the last 50 rows"
    sorted newest-first; `?only_unread=true` narrows to PENDING items.
    """
    q: dict[str, Any] = {"recipient_admin_id": admin.id}
    if only_unread:
        q["is_read"] = False
    rows = (
        await AdminNotification.find(q)
        .sort("-created_at")
        .limit(limit)
        .to_list()
    )
    return APIResponse(data=[_serialise(n) for n in rows])


@router.get("/unread-count", response_model=APIResponse[dict])
async def unread_count(admin: CurrentAdmin):
    """O(1) badge counter for the bell icon. Hit every few seconds /
    on every WS `notification_created` event."""
    count = await AdminNotification.find(
        AdminNotification.recipient_admin_id == admin.id,
        AdminNotification.is_read == False,  # noqa: E712 — beanie equality
    ).count()
    return APIResponse(data={"count": int(count)})


@router.post("/{notification_id}/read", response_model=APIResponse[dict])
async def mark_read(notification_id: str, admin: CurrentAdmin):
    """Mark a single notification read. Only the recipient admin
    themselves can flip their own copy — a broker can't clear an event
    from the super-admin's bell."""
    try:
        oid = PydanticObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Notification not found")
    n = await AdminNotification.get(oid)
    if n is None or n.recipient_admin_id != admin.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not n.is_read:
        n.is_read = True
        n.read_at = now_utc()
        await n.save()
    return APIResponse(data=_serialise(n))


@router.post("/mark-all-read", response_model=APIResponse[dict])
async def mark_all_read(admin: CurrentAdmin):
    """Bulk-flip every unread row for this admin to read in one
    Mongo update. Used by the "Mark all read" link in the bell panel."""
    coll = AdminNotification.get_motor_collection()
    res = await coll.update_many(
        {"recipient_admin_id": admin.id, "is_read": False},
        {"$set": {"is_read": True, "read_at": now_utc()}},
    )
    return APIResponse(data={"marked": int(res.modified_count)})


# ── Broadcast: admin → all their own users ───────────────────────────
# A composer in the admin panel lets any admin/broker push a one-off
# notification (title + message + optional link) to EVERY user in their
# own pool at once. Scoped via `scoped_user_ids` so a broker only reaches
# their subtree and an admin only their clients; super-admin reaches all.
class BroadcastBody(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=1000)
    link: str | None = Field(default=None, max_length=500)
    level: NotificationLevel = NotificationLevel.INFO


@router.get("/broadcast/recipients", response_model=APIResponse[dict])
async def broadcast_recipient_count(
    admin: CurrentAdmin,
    _: None = Depends(require_perm("users", "read")),
):
    """How many users the current actor's broadcast would reach — shown in
    the composer so the admin knows the blast radius before sending."""
    ids = await scoped_user_ids(admin)
    return APIResponse(data={"count": len(ids)})


@router.post("/broadcast", response_model=APIResponse[dict])
async def broadcast_notification(
    body: BroadcastBody,
    admin: CurrentAdmin,
    _: None = Depends(require_perm("users", "read")),
):
    """Insert one SYSTEM notification per user in the actor's pool + push a
    live `notification` WS event to each so it lands in-app instantly (falls
    back to the user's next fetch if the socket is closed)."""
    title = body.title.strip()
    message = body.message.strip()
    if not title or not message:
        raise HTTPException(status_code=400, detail="Title and message are required")
    link = (body.link or "").strip() or None

    recipients = await scoped_user_ids(admin)
    if not recipients:
        return APIResponse(data={"count": 0})

    data: dict[str, Any] = {"source": "admin_broadcast", "sender_id": str(admin.id)}
    if link:
        data["link"] = link

    # ONE stamp for the whole send, instead of `created_at`'s per-row
    # default. `/sent` below regroups these rows by their second, and
    # building them costs ~9 ms per 674 rows (~140 ms per 10 000) — so a
    # send that starts late in a second lands partly in the next one, and
    # the history shows it TWICE with the recipients split between the
    # halves. Measured: ~0.9% of 674-user sends, ~14% at 10 000.
    sent_at = now_utc()

    docs = [
        Notification(
            user_id=uid,
            created_at=sent_at,
            type=NotificationType.SYSTEM,
            level=body.level,
            title=title,
            message=message,
            data=data,
        )
        for uid in recipients
    ]
    await Notification.insert_many(docs)

    # Live push — best-effort; the DB rows above are the source of truth.
    try:
        from app.core.redis_client import publish_batch

        payload = {
            "type": "notification",
            "payload": {
                "title": title,
                "message": message,
                "link": link,
                "level": body.level.value,
            },
        }
        await publish_batch(
            [(f"user:{uid}:notification", payload) for uid in recipients]
        )
    except Exception:
        logger.exception("broadcast_ws_push_failed admin=%s", admin.id)

    # Web Push — wakes the phone/tray even when the PWA is force-stopped or
    # the socket above is closed. Best-effort; no-ops when VAPID is
    # unconfigured. Single bulk subscription query for the whole pool.
    try:
        from app.services import push_service

        await push_service.send_to_users(
            recipients,
            title=title,
            body=message,
            url=link or "/notifications",
            tag=f"mp-broadcast-{admin.id}",
        )
    except Exception:
        logger.exception("broadcast_webpush_failed admin=%s", admin.id)

    try:
        await log_event(
            action=AuditAction.CREATE,
            entity_type="Notification",
            actor_id=admin.id,
            metadata={"action": "broadcast", "count": len(recipients), "title": title, "has_link": bool(link)},
        )
    except Exception:
        logger.exception("broadcast_audit_failed")

    return APIResponse(data={"count": len(recipients)})


# ── Sent history: what actually went OUT to users ────────────────────
# `Notification` is one row PER RECIPIENT, so a bulk send is N rows written
# by a single `insert_many` and there is no batch id to group on. Rows are
# regrouped into one "send" by
# (second, title, message, level, source, sender) — which is what makes the
# sends already sitting in the collection readable with no migration and no
# new field. The cost of the composite: two different senders pushing the
# identical title+message within the same second would fold into one row.
# That needs a `batch_id` to fix properly, and it has never happened.
#
# The window is 90 days by construction, not by choice: `expires_at`
# defaults to +90 d and the collection has a TTL index on it, so anything
# older has been deleted by Mongo. The UI says so.
#
# Cost, honestly: `Notification` indexes `(user_id, created_at)`, so the
# scope `$in` is an index scan — but `$group` is blocking and reads every
# matched row, and a SUPER_ADMIN has no `user_id` filter at all, so that
# arm is a COLLSCAN. What keeps it cheap is the TTL above capping the
# collection at 90 days of sends, plus `?days=` for the usual case. If the
# platform ever outgrows that, the fix is a `created_at` index, not a
# cleverer pipeline.

# Only the senders that know to write `data.source` have one. Everything
# older is identified by the two things it does carry — the literal title
# its sender uses, and `data.category`. Without this the whole history
# reads "system", which is not worth opening.
#
# These slugs are the contract with the frontend's labels; renaming one
# side alone silently relabels history.
_SOURCE_EXPR: dict[str, Any] = {
    "$switch": {
        "branches": [
            {"case": {"$ifNull": ["$data.source", False]}, "then": "$data.source"},
            {"case": {"$eq": ["$title", "Chart lines updated"]}, "then": "chart_lines"},
            {"case": {"$eq": ["$data.category", "payment"]}, "then": "payment_details"},
        ],
        "default": "system",
    }
}


async def _sent_scope(admin: User) -> dict:
    """`user_id` clause for the two sent-history views.

    SUPER_ADMIN deliberately sees EVERY send, platform-wide. The point of
    this screen is the platform owner auditing what their admins pushed at
    whose users, and `scoped_user_ids` would answer the much narrower "my
    own DIRECT clients" (`_pool_clause` → `assigned_admin_id: None`) — the
    same exception, for the same reason, that
    `chart_level_service.notify_levels_changed` makes.

    ``include_closed`` because this is an audit record: a user closed after
    a broadcast still received it, and dropping them would make the
    recipient count drift further from what was actually sent.

    "Further", not "away": this clause is applied to the history read, so
    every count on the screen is per-SCOPE, not per-send. A platform-wide
    broadcast shows a super admin 674 and shows one admin only their own
    slice of it. That is the right number for "what reached MY users",
    which is the question this screen answers — it is NOT the blast radius
    of the original send, and the UI must not label it as one.
    """
    if admin.role == UserRole.SUPER_ADMIN:
        return {}
    return {"user_id": {"$in": await scoped_user_ids(admin, include_closed=True)}}


def _sent_pipeline(
    match: dict, *, source: str | None, skip: int, limit: int
) -> list[dict[str, Any]]:
    """Group the per-recipient rows into sends, then page them.

    Kept separate from the endpoint so the shape is assertable without a
    database. `$facet` so the page and the count of SENDS (not of rows)
    come back in one round trip; the `source` filter sits AFTER `$group`
    because the derived source only exists once it has been computed into
    the group key, and filtering there keeps the total honest.

    `$min` on `created_at` rather than the truncated second, so `sent_at`
    is a real timestamp the recipients endpoint can re-bound exactly.
    """
    pipeline: list[dict[str, Any]] = [
        {"$match": match},
        {
            "$group": {
                "_id": {
                    # `$dateToString`, not `$dateTrunc` — same truncation,
                    # no 5.0 floor.
                    "sec": {
                        "$dateToString": {
                            "date": "$created_at",
                            "format": "%Y-%m-%dT%H:%M:%S",
                        }
                    },
                    "title": "$title",
                    "message": "$message",
                    "level": "$level",
                    "source": _SOURCE_EXPR,
                    "sender_id": {"$ifNull": ["$data.sender_id", None]},
                },
                "recipients": {"$sum": 1},
                "read_count": {"$sum": {"$cond": ["$is_read", 1, 0]}},
                "sent_at": {"$min": "$created_at"},
                "link": {"$first": "$data.link"},
            }
        },
    ]
    if source:
        pipeline.append({"$match": {"_id.source": source}})
    pipeline.append(
        {
            "$facet": {
                "items": [
                    {"$sort": {"sent_at": -1}},
                    {"$skip": skip},
                    {"$limit": limit},
                ],
                "total": [{"$count": "n"}],
            }
        }
    )
    return pipeline


def _page_meta(page: int, page_size: int, total: int) -> dict[str, int]:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/sent", response_model=APIResponse[dict])
async def sent_history(
    admin: CurrentAdmin,
    *,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=120),
    source: str | None = Query(default=None, max_length=40),
    days: int | None = Query(default=None, ge=1, le=90),
    _: None = Depends(require_perm("users", "read")),
):
    """One row per send: what was pushed, by whom, to how many, how many
    read it. Drill into the recipients with `/sent/recipients`."""
    match = await _sent_scope(admin)
    if days:
        match["created_at"] = {"$gte": now_utc() - timedelta(days=days)}
    if q and q.strip():
        # merge_scope, not a bare assignment: the search is an `$or` and so
        # could the scope become, and a dropped SCOPE clause raises nothing
        # — it just shows one admin another admin's sends.
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        merge_scope(match, None, {"$or": [{"title": rx}, {"message": rx}]})

    skip = (page - 1) * page_size
    coll = Notification.get_motor_collection()
    faceted = await coll.aggregate(
        _sent_pipeline(match, source=source, skip=skip, limit=page_size)
    ).to_list(length=1)
    facet = faceted[0] if faceted else {"items": [], "total": []}
    groups = facet["items"]
    total = facet["total"][0]["n"] if facet["total"] else 0

    # One extra query for every sender on the page, not one per row.
    senders: dict[str, dict] = {}
    oids = [
        PydanticObjectId(raw)
        for raw in {g["_id"].get("sender_id") for g in groups}
        # A stale or hand-edited `sender_id` is simply "no sender" — it
        # must not take the page down with an InvalidId.
        if raw and PydanticObjectId.is_valid(raw)
    ]
    if oids:
        async for u in User.get_motor_collection().find(
            {"_id": {"$in": oids}}, {"user_code": 1, "full_name": 1}
        ):
            senders[str(u["_id"])] = u

    items = []
    for g in groups:
        key = g["_id"]
        sender = senders.get(key.get("sender_id") or "")
        items.append(
            {
                "title": key["title"],
                "message": key["message"],
                "level": key["level"],
                "source": key["source"],
                # The id, not just the display name: `/sent/recipients`
                # narrows on it so two same-second sends under one title
                # cannot share a recipient list.
                "sender_id": key.get("sender_id"),
                "sender_name": sender.get("full_name") if sender else None,
                "sender_code": sender.get("user_code") if sender else None,
                "recipients": int(g["recipients"]),
                "read_count": int(g["read_count"]),
                "sent_at": g["sent_at"],
                "link": g.get("link"),
            }
        )
    return APIResponse(data={"items": items, "meta": _page_meta(page, page_size, total)})


def _one_second(raw: str) -> datetime:
    """Parse `sent_at` down to the exact second it names.

    Strict on purpose: this value plus the title is the only thing
    identifying a send, so an unparseable one is a 400 rather than a
    silently open range over the whole collection.
    """
    try:
        dt = datetime.fromisoformat(raw.strip())
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid sent_at") from None
    # The Motor client is tz_aware, so stored values come back aware UTC;
    # a client that sends a bare local-looking stamp is read as UTC rather
    # than shifted by the server's zone.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).replace(microsecond=0)


@router.get("/sent/recipients", response_model=APIResponse[dict])
async def sent_recipients(
    admin: CurrentAdmin,
    *,
    sent_at: str = Query(...),
    title: str = Query(..., min_length=1, max_length=120),
    level: str | None = Query(default=None, max_length=20),
    sender_id: str | None = Query(default=None, max_length=40),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_perm("users", "read")),
):
    """Who one send went to, and who has read it.

    Name and code only — this codebase masks client email and mobile from
    admins behind the `user_contacts` grant, and a recipient list has no
    business re-exposing them.

    The SAME scope as `/sent`, because without it an admin could read
    another admin's recipient list by guessing a timestamp.

    `level` and `sender_id` narrow the key. `/sent` groups on six fields and
    this used to key on two, so two genuinely different sends that landed in
    the same second under the same title would drill down as one list
    longer than either row's `recipients` count. They are optional because
    a send that predates the attribution stamp has no `sender_id` to pass —
    omitting one means "don't narrow on it", never "match anything".
    """
    start = _one_second(sent_at)
    match: dict[str, Any] = {
        "title": title,
        "created_at": {"$gte": start, "$lt": start + timedelta(seconds=1)},
    }
    if level:
        match["level"] = level
    if sender_id:
        match["data.sender_id"] = sender_id
    merge_scope(match, await _sent_scope(admin))

    coll = Notification.get_motor_collection()
    total = await coll.count_documents(match)
    rows = (
        await coll.find(match, {"user_id": 1, "is_read": 1, "read_at": 1})
        .sort("_id", 1)  # stable across pages; created_at ties to the ms
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list(length=page_size)
    )
    users: dict[Any, dict] = {}
    if rows:
        async for u in User.get_motor_collection().find(
            {"_id": {"$in": [r["user_id"] for r in rows]}},
            {"user_code": 1, "full_name": 1},
        ):
            users[u["_id"]] = u

    items = [
        {
            "user_id": str(r["user_id"]),
            "user_code": users.get(r["user_id"], {}).get("user_code"),
            "full_name": users.get(r["user_id"], {}).get("full_name"),
            "is_read": bool(r.get("is_read")),
            "read_at": r.get("read_at"),
        }
        for r in rows
    ]
    return APIResponse(data={"items": items, "meta": _page_meta(page, page_size, total)})
