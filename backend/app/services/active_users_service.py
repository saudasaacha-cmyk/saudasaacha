"""Super-admin roster of every ACTIVE account on the platform.

Answers one question the rest of the panel cannot: who, across the WHOLE
platform, is allowed to trade right now — and of those, who actually has
the app open. Every other user list here is scoped to the caller's own
pool (`scoped_user_filter`), so a super admin whose clients all sit under
sub-admins and brokers sees their own thin slice; this deliberately
ignores scope and walks the entire book, admin and broker login accounts
included, each row labelled with its owner.

Two different notions of "active" sit in the same row on purpose, because
operators conflate them and then act on the wrong one:

* `status` is ACTIVE — the account is not blocked, pending or closed.
* `online` — their socket has checked in within `presence_service.TTL_SEC`.

Contacts are REAL here, not `••••••••`. That mirrors the existing
super-admin-only export (`user_export_service`) and carries the same
guard rails: super admin only, and every file download is written to the
audit log. A generated placeholder (`<code>@noemail…`, `NOMOB…`) prints
as a dash — it is an absence, not an address.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.models.user import User, UserRole, UserStatus
from app.services import presence_service, user_service
from app.utils.time_utils import UTC, to_ist

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


def _contact(value: str | None) -> str:
    return "—" if not value or user_service.is_placeholder_contact(value) else str(value)


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
    rows = await User.find(
        {"role": {"$in": [UserRole.ADMIN.value, UserRole.BROKER.value]}}
    ).to_list()
    return {str(r.id): (r.full_name or r.user_code or str(r.id)) for r in rows}


def _query(
    *, q: str | None, role: str | None, include_demo: bool
) -> dict[str, Any]:
    out: dict[str, Any] = {"status": UserStatus.ACTIVE.value}
    if role:
        out["role"] = role
    if not include_demo:
        out["is_demo"] = {"$ne": True}
        out["email"] = {"$not": re.compile(r"@demo\.local$", re.IGNORECASE)}
    if q:
        regex = re.compile(re.escape(q.strip()), re.IGNORECASE)
        out["$or"] = [
            {"email": regex},
            {"mobile": regex},
            {"user_code": regex},
            {"full_name": regex},
        ]
    return out


async def collect_rows(
    *,
    q: str | None = None,
    role: str | None = None,
    online_only: bool = False,
    include_demo: bool = False,
) -> list[dict[str, Any]]:
    """One row per ACTIVE account, online sessions first.

    Returns the whole matching set rather than a page: the sort is
    "online, longest session first", which cannot be expressed in the
    Mongo query (presence lives in Redis), so paging has to happen after
    the merge. Callers slice what they need.
    """
    presence = await presence_service.online_user_ids()
    users = await User.find(_query(q=q, role=role, include_demo=include_demo)).to_list()
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
        if online_only and since is None:
            continue
        rows.append(
            {
                "id": str(u.id),
                "user_code": u.user_code or "",
                "full_name": u.full_name or "",
                "role": str(u.role.value if hasattr(u.role, "value") else u.role),
                "role_label": _role_label(u),
                "owner": _owner(u),
                # Real, not masked — see the module docstring.
                "email": _contact(u.email),
                "mobile": _contact(u.mobile),
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
