"""Roster of ACTIVE accounts — who may trade, and who is actually here.

Answers one question the rest of the panel cannot. Every other user list
is scoped to the caller's own pool, so a super admin whose clients all sit
under sub-admins and brokers sees their own thin slice and has no way to
ask "who is active across the platform".

Two notions of "active" sit in the same row on purpose, because operators
conflate them and then act on the wrong one:

* `status` is ACTIVE — the account is not blocked, pending or closed.
* `online` — their socket has checked in within `presence_service.TTL_SEC`.

Who sees what is the CALLER's business, not this module's: it takes a
`scope` clause (None = the whole platform, for the super admin; an owned-
pool filter for a granted admin) and a `reveal_contacts` flag, both
resolved by `_resolve_active_users_access` in the users router. Contacts
obey the `user_contacts` permission — an admin may be allowed to see who
is active without being allowed to read their phone number — and the
Excel / PDF builders here render whatever `collect_rows` produced, so a
download can never show more than the page it came from.

A generated placeholder (`<code>@noemail…`, `NOMOB…`) prints as a dash:
it is an absence, not an address.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any

from beanie import PydanticObjectId
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.dependencies import merge_scope
from app.models.user import User, UserRole, UserStatus
from app.services import presence_service, user_service
from app.utils.time_utils import UTC, now_utc, to_ist

COLUMNS: list[tuple[str, str]] = [
    ("user_code", "Code"),
    ("full_name", "Name"),
    ("role_label", "Role"),
    ("owner", "Owner"),
    ("email", "Email"),
    ("mobile", "Mobile"),
    ("online_label", "Online"),
    ("online_since_label", "Online since"),
    ("last_login_label", "Last login"),
    ("created_label", "Joined"),
]

# Admin-tier login accounts are part of the roster (the operator asked for
# "sare admin, broker and super admin ke user bhi"), so unlike the Users
# page there is no role exclusion — only this ordering, which keeps the
# hierarchy readable in a sheet that has no grouping.
_ADMIN_TIER_ROLES: list[str] = [
    UserRole.SUPER_ADMIN.value,
    UserRole.ADMIN.value,
    UserRole.BROKER.value,
    UserRole.EMPLOYEE.value,
]

_ROLE_ORDER: dict[str, int] = {
    UserRole.SUPER_ADMIN.value: 0,
    UserRole.ADMIN.value: 1,
    UserRole.BROKER.value: 2,
    UserRole.EMPLOYEE.value: 3,
    UserRole.MASTER.value: 4,
    UserRole.DEALER.value: 5,
    UserRole.CLIENT.value: 6,
}


def _role_label(u: User) -> str:
    """Human role, with the sub-broker tier spelled out.

    A sub-broker carries BROKER like its parent, so the raw role alone
    loses the distinction the Brokers page makes a point of showing.
    """
    role = str(u.role.value if hasattr(u.role, "value") else u.role)
    if role == UserRole.BROKER.value and u.assigned_broker_id:
        return "Sub-broker"
    return role.replace("_", " ").capitalize()


def _stamp(dt: datetime | None) -> str:
    return to_ist(dt).strftime("%d-%m-%Y %H:%M") if dt else "—"


def _elapsed(seconds: int) -> str:
    """`2h 14m` — how long this session has been up."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h {minutes % 60}m"


async def _owner_names() -> dict[str, str]:
    """Owner labels for every admin and broker — a projection, on purpose.

    This runs on every 20 s poll of the page and every export, and all it
    produces is a label, so hydrating full User documents to build one is
    the expensive half of a request that has no business being expensive.
    """
    cursor = User.get_motor_collection().find(
        {"role": {"$in": [UserRole.ADMIN.value, UserRole.BROKER.value]}},
        {"full_name": 1, "user_code": 1},
    )
    return {
        str(d["_id"]): (d.get("full_name") or d.get("user_code") or str(d["_id"]))
        async for d in cursor
    }


def _query(
    *,
    q: str | None,
    role: str | None,
    include_demo: bool,
    scope: dict[str, Any] | None,
    clients_only: bool,
    online_ids: list[PydanticObjectId] | None = None,
    logged_in_since: datetime | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"status": UserStatus.ACTIVE.value}
    if logged_in_since is not None:
        # Recent LOGIN, which is not the same question as recent activity:
        # someone who signed in on Monday and has kept the tab open since
        # is trading today and will not appear here. The column header says
        # "logged in" rather than "active" so the row list cannot be read
        # as the stronger claim. `$gte` also drops rows with no
        # `last_login_at` at all, which is what we want — never signed in
        # is not recently signed in.
        out["last_login_at"] = {"$gte": logged_in_since}
    # Both clauses land on `role`, where Mongo ANDs them: a caller-supplied
    # role NARROWS this roster and can never widen it. Letting it replace
    # the exclusion handed a granted ADMIN asking `?role=BROKER` exactly
    # the broker and employee logins the exclusion exists to keep out.
    role_clause: dict[str, Any] = {}
    if clients_only:
        # A granted ADMIN's roster is their CLIENTS. Their own pool clause
        # also matches the broker and employee login accounts they created,
        # and those are managed on their own pages.
        role_clause["$nin"] = _ADMIN_TIER_ROLES
    if role:
        role_clause["$eq"] = role
    if role_clause:
        out["role"] = role_clause
    if online_ids is not None:
        # Presence lives in Redis, so an online-only view can only avoid
        # reading the whole collection by handing Mongo the ids it found.
        out["_id"] = {"$in": online_ids}
    if not include_demo:
        out["is_demo"] = {"$ne": True}
        out["email"] = {"$not": re.compile(r"@demo\.local$", re.IGNORECASE)}
    # Scope and search can BOTH be `$or`s, so merge_scope ANDs them instead
    # of letting one dict key hold only the second.
    search: dict[str, Any] | None = None
    if q:
        regex = re.compile(re.escape(q.strip()), re.IGNORECASE)
        search = {
            "$or": [
                {"email": regex},
                {"mobile": regex},
                {"user_code": regex},
                {"full_name": regex},
            ]
        }
    return merge_scope(out, scope, search)


async def collect_rows(
    *,
    q: str | None = None,
    role: str | None = None,
    online_only: bool = False,
    include_demo: bool = False,
    scope: dict[str, Any] | None = None,
    clients_only: bool = False,
    reveal_contacts: bool = False,
    logged_in_hours: int | None = None,
) -> list[dict[str, Any]]:
    """One row per ACTIVE account, online sessions first.

    Returns the whole matching set rather than a page: the sort is
    "online, longest session first", which cannot be expressed in the
    Mongo query (presence lives in Redis), so paging has to happen after
    the merge. Callers slice what they need.

    `scope` is a Mongo clause limiting which accounts are visible — `None`
    for the super admin's platform-wide view, the caller's owned pool for a
    granted ADMIN. `reveal_contacts` decides whether email / mobile come
    back real or masked (`user_contacts` permission) — it defaults to
    masked, so a caller that forgets the kwarg under-shares instead of
    printing every contact on the platform.
    """
    presence = await presence_service.online_user_ids()
    online_ids: list[PydanticObjectId] | None = None
    if online_only:
        # Checked rather than cast: a junk presence key is Redis' problem,
        # not a 500 on the page.
        online_ids = [
            PydanticObjectId(uid) for uid in presence if PydanticObjectId.is_valid(uid)
        ]
        if not online_ids:
            return []
    users = await User.find(
        _query(
            q=q,
            role=role,
            include_demo=include_demo,
            scope=scope,
            clients_only=clients_only,
            online_ids=online_ids,
            logged_in_since=(
                now_utc() - timedelta(hours=logged_in_hours)
                if logged_in_hours
                else None
            ),
        )
    ).to_list()
    if not users:
        return []

    names = await _owner_names()

    def _owner(u: User) -> str:
        if u.assigned_broker_id:
            return f"Broker: {names.get(str(u.assigned_broker_id), '—')}"
        if u.assigned_admin_id:
            return f"Admin: {names.get(str(u.assigned_admin_id), '—')}"
        return "Super admin"

    rows: list[dict[str, Any]] = []
    for u in users:
        since = presence.get(str(u.id))
        rows.append(
            {
                "id": str(u.id),
                "user_code": u.user_code or "",
                "full_name": u.full_name or "",
                "role": str(u.role.value if hasattr(u.role, "value") else u.role),
                "role_label": _role_label(u),
                "owner": _owner(u),
                # Real or masked, per the actor's `user_contacts` grant —
                # the same rule the All Users page applies, so a page and
                # its download can never disagree with each other.
                "email": user_service.contact_display(u.email, reveal=reveal_contacts),
                "mobile": user_service.contact_display(u.mobile, reveal=reveal_contacts),
                "status": str(u.status.value if hasattr(u.status, "value") else u.status),
                "is_demo": bool(getattr(u, "is_demo", False)),
                "online": since is not None,
                "online_since": since,
                "last_login_at": u.last_login_at,
                "created_at": u.created_at,
            }
        )

    # Online first (longest-running session at the top), then by tier, then
    # newest account — so the people actually on the platform are never
    # buried under a page of dormant rows.
    rows.sort(
        key=lambda r: (
            0 if r["online"] else 1,
            r["online_since"] or 0,
            _ROLE_ORDER.get(r["role"], 99),
        )
    )
    return rows


def _display(row: dict[str, Any]) -> dict[str, Any]:
    """Row as it prints in a file — timestamps in IST, booleans as words."""
    since = row.get("online_since")
    now = int(time.time())
    return {
        **row,
        "online_label": "Yes" if row.get("online") else "No",
        "online_since_label": (
            f"{_stamp(datetime.fromtimestamp(since, UTC))} "
            f"({_elapsed(max(0, now - since))})"
            if since
            else "—"
        ),
        "last_login_label": _stamp(row.get("last_login_at")),
        "created_label": _stamp(row.get("created_at")),
    }


def _title(rows: list[dict[str, Any]]) -> str:
    online = sum(1 for r in rows if r.get("online"))
    return f"Active users — {len(rows)} active, {online} online now"


def to_xlsx(rows: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Active users"

    head_fill = PatternFill("solid", fgColor="0B1220")
    head_font = Font(bold=True, color="FFFFFF")
    online_fill = PatternFill("solid", fgColor="DCFCE7")
    ws.cell(row=1, column=1, value=_title(rows)).font = Font(bold=True, size=13)
    for c, (_key, head) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=2, column=c, value=head)
        cell.fill, cell.font = head_fill, head_font
        cell.alignment = Alignment(horizontal="center")

    for r, row in enumerate([_display(x) for x in rows], start=3):
        for c, (key, _head) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=r, column=c, value=row.get(key))
            # Tint the rows that are online so the live ones are findable
            # in a sheet of a thousand.
            if row.get("online"):
                cell.fill = online_fill

    widths = {
        "full_name": 22,
        "owner": 24,
        "email": 28,
        "mobile": 14,
        "online_since_label": 24,
        "last_login_label": 17,
        "created_label": 17,
    }
    for c, (key, head) in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(c)].width = widths.get(
            key, max(11, len(head) + 2)
        )
    ws.freeze_panes = "A3"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(rows: list[dict[str, Any]]) -> bytes:
    """Landscape A4. Email, name and owner wrap; the rest are short."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    weights = {
        "user_code": 1.0,
        "full_name": 1.6,
        "role_label": 1.0,
        "owner": 1.6,
        "email": 2.4,
        "mobile": 1.1,
        "online_label": 0.7,
        "online_since_label": 1.7,
        "last_login_label": 1.3,
        "created_label": 1.3,
    }
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=_title(rows),
    )
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontSize = 6.5
    body.leading = 8

    data: list[list[Any]] = [[h for _k, h in COLUMNS]]
    online_rows: list[int] = []
    for i, row in enumerate([_display(x) for x in rows], start=1):
        if row.get("online"):
            online_rows.append(i)
        data.append(
            [
                (
                    Paragraph(str(row.get(k, "")), body)
                    if k in ("full_name", "owner", "email")
                    else str(row.get(k, ""))
                )
                for k, _h in COLUMNS
            ]
        )

    avail = landscape(A4)[0] - 20 * mm
    total_w = sum(weights[k] for k, _h in COLUMNS)
    table = Table(
        data,
        colWidths=[avail * weights[k] / total_w for k, _h in COLUMNS],
        repeatRows=1,
        hAlign="LEFT",
    )
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1220")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    # Same green as the sheet — applied last so it wins over ROWBACKGROUNDS.
    style += [
        ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#DCFCE7")) for i in online_rows
    ]
    table.setStyle(TableStyle(style))

    doc.build(
        [
            Paragraph(f"<b>{_title(rows)}</b>", styles["Title"]),
            Spacer(1, 4 * mm),
            table,
        ]
    )
    return buf.getvalue()
