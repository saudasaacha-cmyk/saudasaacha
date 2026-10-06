"""Admin chart lines: Excel round-trip + the user-side resolver.

The admin picks a segment, downloads a workbook pre-filled with every
instrument in it, types a price under each line column, and uploads it
back. The colour and the label of each line are set ONCE at the top of the
sheet and apply to every instrument. Each price becomes a horizontal line on that instrument's
chart in the colour that was given.

Ownership and the user-side cascade mirror ``crypto_config_service`` exactly —
the same resolver rule already backs company banks and crypto configs, and a
second, subtly different one would be a bug waiting to happen.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from io import BytesIO
from typing import Any

from beanie import PydanticObjectId
from beanie.operators import In
from bson import Decimal128
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from app.models.chart_level import ChartLevel, ChartLevelEntry, ChartLevelVisibility
from app.models.instrument import Instrument
from app.models.user import User, UserRole, UserStatus
from app.utils.decimal_utils import to_decimal

# How many line columns a FRESH template ships with, and how many slots the
# inline editor shows. The import has no cap: the operator adds as many
# "Line N" columns as they want and every one of them is read.
DEFAULT_LEVELS = 6

# Readable defaults so a sheet filled in without touching the colour row
# still yields DISTINGUISHABLE lines rather than six identical ones.
DEFAULT_COLORS = [
    "#E31E24", "#0EA5E9", "#16A34A", "#F59E0B", "#7C3AED", "#EC4899",
]

TREND_VALUES = ("Uptrend", "Downtrend", "Sideways")

# What an operator actually types. Anything unrecognised is dropped rather
# than stored, so a typo shows as "no trend" instead of a chip reading "Dwn".
_TREND_ALIASES: dict[str, str] = {
    "UP": "Uptrend", "UPTREND": "Uptrend", "UP TREND": "Uptrend",
    "BULLISH": "Uptrend", "BULL": "Uptrend", "BUY": "Uptrend",
    "DOWN": "Downtrend", "DOWNTREND": "Downtrend", "DOWN TREND": "Downtrend",
    "BEARISH": "Downtrend", "BEAR": "Downtrend", "SELL": "Downtrend",
    "SIDE": "Sideways", "SIDEWAYS": "Sideways", "SIDE WAYS": "Sideways",
    "FLAT": "Sideways", "NEUTRAL": "Sideways", "RANGE": "Sideways",
}

_HEX_RE = re.compile(r"^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")

# Colour words an operator is likely to type instead of a hex code.
_NAMED: dict[str, str] = {
    "red": "#E31E24", "green": "#16A34A", "blue": "#2563EB", "yellow": "#EAB308",
    "orange": "#F59E0B", "purple": "#7C3AED", "violet": "#7C3AED", "pink": "#EC4899",
    "cyan": "#06B6D4", "sky": "#0EA5E9", "black": "#111111", "white": "#FFFFFF",
    "grey": "#6B7280", "gray": "#6B7280", "brown": "#92400E", "teal": "#14B8A6",
    "lime": "#84CC16", "magenta": "#D946EF", "gold": "#D4AF37", "silver": "#C0C0C0",
}

# The columns that come before the line columns. Everything to the RIGHT of
# Trend is a line, whatever its heading says — that is what "Line N" means:
# the operator adds columns and the parser reads as many as it finds.
FIXED_HEADERS = ["Token", "Symbol", "Segment", "Trend"]


def _round_like_tick(price: Decimal, tick: Any) -> Decimal:
    """Trim a price to the instrument's DECIMAL PLACES — not to a tick multiple.

    Excel hands back the cached value of a formula, so a cell that reads
    4249.17 arrives as 4249.17065447777 and every chip and line label then
    carries fourteen digits. Rounding to the tick's precision fixes that
    while leaving the operator's own number alone; snapping to a tick
    MULTIPLE would silently move 4249.17 to 4249.15 on a 0.05-tick
    instrument, and a level is a marker, not an order.
    """
    exp = -2
    try:
        t = to_decimal(tick)
        if t > 0 and isinstance(t.as_tuple().exponent, int):
            exp = int(t.as_tuple().exponent)
    except Exception:  # noqa: BLE001
        pass
    places = min(max(-exp, 0), 8)
    q = price.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN).normalize()
    # normalize() turns 100.00 into 1E+2 — put it back into plain notation.
    return q.quantize(Decimal(1)) if q.as_tuple().exponent > 0 else q


# ── segment labels ───────────────────────────────────────────────────
# Two segment taxonomies exist in this codebase: the netting one the Segment
# Settings page shows (NSE_STK_FUT, FOREX, CRYPTO …) and the one instruments
# actually carry (NSE_FUTURE, CRYPTO_SPOT, FOREX …). They overlap but are not
# the same, so the picker is labelled from BOTH — netting display names are
# reused rather than retyped, and the instrument-only names get their own
# entries. Anything unmapped falls back to a title-cased form instead of the
# raw enum, so a new segment can never show up as SCREAMING_SNAKE_CASE.
_INSTRUMENT_SEGMENT_LABELS: dict[str, str] = {
    "NSE_EQUITY": "NSE Equity",
    "NSE_FUTURE": "Stock Future",
    "NSE_INDEX_FUTURE": "Index Future",
    "NSE_STOCK_OPTION_BUY": "Stock Option — Buy",
    "NSE_STOCK_OPTION_SELL": "Stock Option — Sell",
    "NSE_INDEX_OPTION_BUY": "Index Option — Buy",
    "NSE_INDEX_OPTION_SELL": "Index Option — Sell",
    "BSE_EQUITY": "BSE Equity",
    "BSE_FUTURE": "BSE Future",
    "BSE_INDEX_FUTURE": "BSE Index Future",
    "BSE_OPTION_BUY": "BSE Option — Buy",
    "BSE_OPTION_SELL": "BSE Option — Sell",
    "MCX_FUTURE": "MCX Future",
    "MCX_OPTION_BUY": "MCX Option — Buy",
    "MCX_OPTION_SELL": "MCX Option — Sell",
    "CDS_FUTURE": "Currency Future",
    "CDS_OPTION_BUY": "Currency Option — Buy",
    "CDS_OPTION_SELL": "Currency Option — Sell",
    "CRYPTO_SPOT": "Crypto Spot",
    "CRYPTO_FUTURE": "Crypto Future",
}


def segment_label(name: str) -> str:
    from app.services.netting_service import SEGMENT_DEFAULTS

    raw = str(name or "").strip()
    if not raw:
        return ""
    for d in SEGMENT_DEFAULTS:
        if d.get("name") == raw:
            return str(d.get("displayName") or raw)
    if raw in _INSTRUMENT_SEGMENT_LABELS:
        return _INSTRUMENT_SEGMENT_LABELS[raw]
    return raw.replace("_", " ").title()


async def available_segments() -> list[dict[str, Any]]:
    """Segments that actually HAVE instruments, with counts.

    Deliberately not the SegmentType enum: instruments carry values the enum
    doesn't contain (FOREX, COMMODITIES), so an enum-driven picker silently
    made those two impossible to configure — and offered thirteen segments
    that would download an empty sheet.
    """
    rows = await Instrument.get_motor_collection().aggregate(
        [
            {"$group": {"_id": "$segment", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
        ]
    ).to_list(length=None)
    out: list[dict[str, Any]] = []
    for r in rows:
        name = r.get("_id")
        if not name:
            continue
        out.append(
            {"value": str(name), "label": segment_label(str(name)), "count": r.get("count", 0)}
        )
    return out


# ── ownership ────────────────────────────────────────────────────────
def owner_filter_for_admin(admin: User) -> dict[str, PydanticObjectId | None]:
    """The (owner_admin_id, owner_broker_id) pair identifying THIS actor's
    rows. Super-admin writes the platform default (both null)."""
    if admin.role == UserRole.SUPER_ADMIN:
        return {"owner_admin_id": None, "owner_broker_id": None}
    if admin.role == UserRole.BROKER:
        return {"owner_admin_id": None, "owner_broker_id": admin.id}
    return {"owner_admin_id": admin.id, "owner_broker_id": None}


def normalize_color(raw: Any, fallback: str) -> str:
    """Accept '#RGB', '#RRGGBB', bare hex, or a colour name.

    Anything unrecognised falls back rather than passing through: an invalid
    CSS colour reaches TradingView as a black or invisible line with no error
    anywhere, which reads as "the feature is broken".
    """
    s = str(raw or "").strip()
    if not s:
        return fallback
    if _HEX_RE.match(s):
        return s.upper()
    if _HEX_RE.match("#" + s):
        return ("#" + s).upper()
    return _NAMED.get(s.lower(), fallback)


def normalize_trend(raw: Any) -> str | None:
    """'down', 'DOWNTREND', 'Bearish' -> 'Downtrend'. Unknown -> None."""
    s = " ".join(str(raw or "").split()).upper()
    if not s:
        return None
    return _TREND_ALIASES.get(s)


# ── one row for every expiry of the same underlying ──────────────────
# GOLD26OCTFUT, GOLD26DECFUT and GOLD27FEBFUT are the same metal. An admin
# who draws support and resistance on gold means all of them, and setting the
# same four prices on every contract — then again when a contract expires —
# is the whole complaint. Those lines are stored against a ROOT pseudo-token
# ("ROOT:MCX:GOLD"); a contract with no row of its own falls back to it, so
# the levels are set ONCE and a single contract can still override them by
# carrying its own row.
#
# Futures only. An option's strike is part of its identity — NIFTY 22600 CE
# and NIFTY 23000 PE share an underlying but not a price range — so grouping
# those under one set of lines would be meaningless.
ROOT_PREFIX = "ROOT:"
_ROOT_RE = re.compile(r"^([A-Z][A-Z&\-]*?)\d[\dA-Z]*FUT$")


def symbol_root(symbol: str) -> str | None:
    """"GOLD26OCTFUT" -> "GOLD". Not a futures symbol -> None.

    ponytail: this is the alphabetic prefix, so NIFTYNXT50 reads back as
    "NIFTYNXT". Every expiry of that underlying still maps to the SAME root,
    which is all the grouping needs — only the label is clipped. Give
    Instrument a real `underlying` field if the spelling ever matters.
    """
    m = _ROOT_RE.match((symbol or "").strip().upper())
    return m.group(1) if m else None


def root_token_for(inst: Instrument) -> str | None:
    root = symbol_root(inst.symbol or "")
    if not root:
        return None
    return f"{ROOT_PREFIX}{str(inst.exchange or '').upper()}:{root}"


def is_root_token(token: str) -> bool:
    return str(token or "").startswith(ROOT_PREFIX)


def root_display(token: str) -> str:
    """"ROOT:MCX:GOLD" -> "GOLD — all expiries"."""
    return f"{str(token).split(':')[-1]} — all expiries"


def _nearest_contract(contracts: list[Instrument]) -> Instrument:
    """The contract an admin is actually looking at: nearest expiry still
    ahead, else the last one. Its tick size and live price stand in for the
    root row, which has neither of its own."""
    now = datetime.now(UTC).replace(tzinfo=None)

    def exp(c: Instrument):
        e = getattr(c, "expiry", None)
        if e is None:
            return None
        return e.replace(tzinfo=None) if e.tzinfo else e

    ahead = sorted(
        (c for c in contracts if exp(c) is not None and exp(c) >= now), key=exp
    )
    if ahead:
        return ahead[0]
    dated = sorted((c for c in contracts if exp(c) is not None), key=exp)
    return dated[-1] if dated else contracts[0]


def group_by_root(instruments: list[Instrument]) -> dict[str, list[Instrument]]:
    out: dict[str, list[Instrument]] = {}
    for i in instruments:
        rt = root_token_for(i)
        if rt:
            out.setdefault(rt, []).append(i)
    return out


async def contracts_for_root(rt: str) -> list[Instrument]:
    """Every contract the root row covers."""
    try:
        exch, root = rt[len(ROOT_PREFIX):].split(":", 1)
    except ValueError:
        return []
    rows = await Instrument.find(
        {"exchange": exch, "symbol": {"$regex": rf"^{re.escape(root)}\d"}}
    ).to_list()
    return [i for i in rows if root_token_for(i) == rt]


# ── template ─────────────────────────────────────────────────────────
# Sheet shape (the operator's own design):
#
#   row 1   Token | Symbol | Segment | Trend | Line 1 | Line 2 | ... | Line N
#   row 2   Color |        |         |       | #E31E24| #0EA5E9| ... <- ONE colour per line, all instruments
#   row 3   Label |        |         |       | MF     | D1     | ... <- ONE label  per line, all instruments
#   row 4+  NATGAS| NATGAS | Commod. | Down  | 1      | 1.1    | ...  <- just prices
#
# The colour and the label used to be repeated on every single row, which
# meant retyping them for all 742 instruments to change one colour. They are
# now set once at the top and applied to every row below.
LINE_ROW_COLOR = 2
LINE_ROW_LABEL = 3
DATA_ROW_START = 4


def _line_settings(
    saved: list[ChartLevel], count: int
) -> tuple[list[str], list[str]]:
    """The colour + label to put in rows 2 and 3.

    Seeded from whichever saved instrument carries the most lines, so a
    downloaded sheet round-trips what is already configured instead of
    resetting it to the defaults.
    """
    src = max(saved, key=lambda r: len(r.levels), default=None)
    colors, labels = [], []
    for i in range(count):
        entry = src.levels[i] if src and i < len(src.levels) else None
        colors.append(entry.color if entry else DEFAULT_COLORS[i % len(DEFAULT_COLORS)])
        labels.append((entry.label or "") if entry else "")
    return colors, labels


async def build_template(admin: User, segment: str) -> bytes:
    """Workbook of every instrument in `segment`, pre-filled with whatever
    this admin already saved so editing is a round-trip, not a retype."""
    instruments = await Instrument.find(Instrument.segment == segment).to_list()
    instruments.sort(key=lambda i: (i.symbol or ""))

    f = owner_filter_for_admin(admin)
    existing = {
        r.token: r
        for r in await ChartLevel.find(
            ChartLevel.owner_admin_id == f["owner_admin_id"],
            ChartLevel.owner_broker_id == f["owner_broker_id"],
            ChartLevel.segment == segment,
        ).to_list()
    }

    # Ship enough line columns for everything already saved — downloading a
    # sheet must never silently drop lines the admin had configured.
    saved = list(existing.values())
    n_lines = max(DEFAULT_LEVELS, max((len(r.levels) for r in saved), default=0))
    colors, labels = _line_settings(saved, n_lines)

    wb = Workbook()
    ws = wb.active
    # Sheet tab and the Segment column both show the friendly label, matching
    # the Segment Settings page. The parser keys off Token, never these.
    label = segment_label(segment)
    ws.title = (label or "Levels")[:31]

    head_fill = PatternFill("solid", fgColor="0B1220")
    head_font = Font(bold=True, color="FFFFFF")
    headers = FIXED_HEADERS + [f"Line {i + 1}" for i in range(n_lines)]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill, cell.font = head_fill, head_font
        cell.alignment = Alignment(horizontal="center")

    # Rows 2 and 3: one colour and one label per line, for every instrument.
    setting_fill = PatternFill("solid", fgColor="E2E8F0")
    for row_no, title, values in (
        (LINE_ROW_COLOR, "Color", colors),
        (LINE_ROW_LABEL, "Label", labels),
    ):
        marker = ws.cell(row=row_no, column=1, value=title)
        marker.font = Font(bold=True)
        marker.fill = setting_fill
        for i, v in enumerate(values):
            cell = ws.cell(row=row_no, column=len(FIXED_HEADERS) + 1 + i, value=v)
            cell.fill = setting_fill
            cell.alignment = Alignment(horizontal="center")

    trend_col = FIXED_HEADERS.index("Trend") + 1
    # Root rows first: fill GOLD once and every GOLD contract draws those
    # lines. A contract row below still wins for that one contract.
    roots = group_by_root(instruments)
    sheet_rows: list[tuple[str, str, Instrument]] = [
        (rt, root_display(rt), _nearest_contract(cs)) for rt, cs in sorted(roots.items())
    ]
    sheet_rows += [(i.token, i.symbol, i) for i in instruments]

    for r, (row_token, row_symbol, inst) in enumerate(sheet_rows, start=DATA_ROW_START):
        ws.cell(row=r, column=1, value=row_token)
        ws.cell(row=r, column=2, value=row_symbol)
        ws.cell(row=r, column=3, value=segment_label(str(inst.segment)))
        saved_row = existing.get(row_token)
        ws.cell(row=r, column=trend_col, value=saved_row.trend if saved_row else None)
        for i in range(n_lines):
            entry = (
                saved_row.levels[i]
                if saved_row and i < len(saved_row.levels)
                else None
            )
            if entry is None:
                continue
            ws.cell(
                row=r,
                column=len(FIXED_HEADERS) + 1 + i,
                value=float(_round_like_tick(entry.price.to_decimal(), inst.tick_size)),
            )

    for c in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 16
    ws.freeze_panes = f"A{DATA_ROW_START}"

    # A validation dropdown on Trend beats an operator guessing the spelling.
    dv = DataValidation(
        type="list", formula1='"' + ",".join(TREND_VALUES) + '"', allow_blank=True
    )
    ws.add_data_validation(dv)
    col = get_column_letter(trend_col)
    last = max(DATA_ROW_START, DATA_ROW_START + len(sheet_rows) - 1)
    dv.add(f"{col}{DATA_ROW_START}:{col}{last}")

    # A second sheet documenting the columns — whoever fills this in is not
    # the person who wrote the parser.
    guide = wb.create_sheet("How to fill")
    rows = [
        ("Column / Row", "What to put"),
        ("Token", "Leave as-is. This is what identifies the instrument."),
        ("GOLD — all expiries", "The first rows of the sheet. Fill ONE of these and every expiry of that "
         "underlying draws those lines — GOLD26OCTFUT, GOLD26DECFUT, and next year's too."),
        ("", "A contract's OWN row still wins over its 'all expiries' row, if you need one to differ."),
        ("", "To hand a contract back to the family, blank ITS prices — then it follows the underlying again."),
        ("Symbol / Segment", "Leave as-is. For reading only."),
        ("Trend", "Uptrend, Downtrend or Sideways. Shown on the user's chart. Blank = no trend."),
        ("Line 1 ... Line N", "The price to draw that line at. Blank = no line on that instrument."),
        ("", "Add as many Line columns as you need — every column to the right of Trend is read."),
        ("Row 2 (Color)", "ONE colour per line, used for every instrument. "
         "Hex like #E31E24, or a name: red, green, blue, orange, purple, ..."),
        ("Row 3 (Label)", "ONE label per line, used for every instrument. e.g. MF, D1, D2, S2, DN."),
        ("", ""),
        ("Note", "Colour and label are set ONCE at the top — you no longer repeat them on every instrument."),
        ("Note", "Re-uploading REPLACES that instrument's lines with what the sheet says."),
        ("Note", "A row with every price blank CLEARS that instrument's lines."),
        ("Note", "An older sheet with Line/Color/Price per instrument still imports as before."),
    ]
    for r, (a, b) in enumerate(rows, start=1):
        guide.cell(row=r, column=1, value=a).font = Font(bold=(r == 1))
        guide.cell(row=r, column=2, value=b).font = Font(bold=(r == 1))
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 96

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── import ───────────────────────────────────────────────────────────
_COL_RE = re.compile(r"\s*(price|colou?r|line|label)\s*#?\s*(\d+)\s*$", re.I)


def _column_map(header: tuple[Any, ...]) -> dict[int, dict[str, int]]:
    """LEGACY layout only: {level index: {"price"/"color"/"label": column}}.

    Sheets downloaded before the colour/label moved to their own rows carry
    a Price/Color/Line trio per level. They are read off the HEADING rather
    than fixed offsets, so an old sheet — four levels or six, Price first or
    Line first — still imports. Returns {} for the current layout, which has
    no "Price 1" column at all; that is what selects the new parser.
    """
    out: dict[int, dict[str, int]] = {}
    for idx, cell in enumerate(header or ()):
        m = _COL_RE.match(str(cell or ""))
        if not m:
            continue
        kind = m.group(1).lower()
        key = "price" if kind == "price" else "color" if kind.startswith("col") else "label"
        out.setdefault(int(m.group(2)) - 1, {})[key] = idx
    return {k: v for k, v in out.items() if "price" in v}


def _cell(row: tuple[Any, ...], cols: dict[str, int], key: str) -> Any:
    idx = cols.get(key)
    return row[idx] if idx is not None and len(row) > idx else None


def _text(cell: Any) -> str:
    return str(cell).strip() if cell is not None else ""


# Row 2 and row 3 carry the colours and the labels rather than an instrument.
# Recognised by a blank Token cell — which is how the operator's own sheet
# has them — or by the marker word the downloaded template writes there.
_SETTING_MARKERS = {"color", "colour", "colors", "colours", "label", "labels"}


def _is_setting_row(row: tuple[Any, ...]) -> bool:
    return _text(row[0] if row else None).lower() in _SETTING_MARKERS | {""}


def _looks_like_colors(row: tuple[Any, ...], line_cols: list[int]) -> bool:
    """A colour row has hex codes / colour names in it; a label row has MF,
    D1, S2. Checked by content so the two can be in either order, and a
    sheet with only one of them still reads correctly."""
    for idx in line_cols:
        v = _text(row[idx] if len(row) > idx else None)
        if v and (_HEX_RE.match(v) or _HEX_RE.match("#" + v) or v.lower() in _NAMED):
            return True
    return False


def _new_layout(rows: list[tuple[Any, ...]]) -> dict[str, Any]:
    """Read the header, the colour row and the label row off a current sheet.

    Every column to the RIGHT of Trend (or of Segment, on a sheet without
    one) is a line — heading text is ignored entirely, so "Line N",
    "Line 12" and "R3" all work and the operator can add as many as they
    like. Trailing spreadsheet padding is dropped: a column counts only if
    it has a heading, a colour or a label.
    """
    header = rows[0]
    fixed = [_text(c).lower() for c in header[: len(FIXED_HEADERS) + 1]]
    trend_idx = fixed.index("trend") if "trend" in fixed else None
    start = (trend_idx + 1) if trend_idx is not None else (
        fixed.index("segment") + 1 if "segment" in fixed else 3
    )

    settings: list[tuple[Any, ...]] = []
    body_start = 1
    while body_start < len(rows) and len(settings) < 2 and _is_setting_row(rows[body_start]):
        settings.append(rows[body_start])
        body_start += 1

    width = max((len(r) for r in [header, *settings]), default=start)
    line_cols = [
        i
        for i in range(start, width)
        if _text(header[i] if len(header) > i else None)
        or any(_text(r[i] if len(r) > i else None) for r in settings)
    ]

    colors_row = next((r for r in settings if _looks_like_colors(r, line_cols)), None)
    labels_row = next((r for r in settings if r is not colors_row), None)

    colors, labels = [], []
    for n, idx in enumerate(line_cols):
        raw_c = colors_row[idx] if colors_row is not None and len(colors_row) > idx else None
        raw_l = labels_row[idx] if labels_row is not None and len(labels_row) > idx else None
        colors.append(normalize_color(raw_c, DEFAULT_COLORS[n % len(DEFAULT_COLORS)]))
        labels.append(_text(raw_l) or None)

    return {
        "line_cols": line_cols,
        "colors": colors,
        "labels": labels,
        "trend_idx": trend_idx,
        "body_start": body_start,
    }


def _parse_price(
    raw: Any, inst: Instrument, slot: int, errors: list[str]
) -> Decimal | None:
    """One price cell. None = no line here; problems are collected, not
    raised, because an operator with forty rows wants every error at once."""
    if raw in (None, ""):
        return None
    try:
        # Operators paste formatted numbers ("4,249.17") straight out of
        # another sheet — a comma shouldn't reject the row.
        clean = raw.replace(",", "").strip() if isinstance(raw, str) else raw
        price = _round_like_tick(to_decimal(clean), inst.tick_size)
    except Exception:  # noqa: BLE001
        errors.append(f"{inst.symbol}: 'Line {slot}' = {raw!r} is not a number")
        return None
    if price <= 0:
        errors.append(f"{inst.symbol}: 'Line {slot}' must be greater than 0")
        return None
    return price


def _legacy_entries(
    row: tuple[Any, ...],
    cols: dict[int, dict[str, int]],
    inst: Instrument,
    errors: list[str],
) -> list[ChartLevelEntry]:
    """Old layout: colour and label repeated on every instrument's row."""
    entries: list[ChartLevelEntry] = []
    for i in sorted(cols):
        c = cols[i]
        raw = row[c["price"]] if len(row) > c["price"] else None
        price = _parse_price(raw, inst, i + 1, errors)
        if price is None:
            continue
        lbl = _cell(row, c, "label")
        entries.append(
            ChartLevelEntry(
                price=Decimal128(str(price)),
                color=normalize_color(
                    _cell(row, c, "color"), DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
                ),
                label=(str(lbl).strip() or None) if lbl else None,
            )
        )
    return entries


def _line_entries(
    row: tuple[Any, ...],
    layout: dict[str, Any],
    inst: Instrument,
    errors: list[str],
) -> list[ChartLevelEntry]:
    """Current layout: the row carries prices only. Colour and label come
    from rows 2 and 3, so they are the same on every instrument."""
    entries: list[ChartLevelEntry] = []
    for n, idx in enumerate(layout["line_cols"]):
        price = _parse_price(
            row[idx] if len(row) > idx else None, inst, n + 1, errors
        )
        if price is None:
            continue
        entries.append(
            ChartLevelEntry(
                price=Decimal128(str(price)),
                color=layout["colors"][n],
                label=layout["labels"][n],
            )
        )
    return entries


async def import_workbook(admin: User, data: bytes) -> dict[str, Any]:
    """Parse an uploaded template and upsert this admin's rows.

    Collects problems instead of raising on the first bad cell — an operator
    with forty rows wants every error at once, not one per upload.
    """
    try:
        wb = load_workbook(BytesIO(data), data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Not a readable .xlsx file: {exc}") from exc
    ws = wb.worksheets[0]

    rows = list(ws.iter_rows(min_row=1, values_only=True))
    if not rows:
        raise ValueError("The sheet is empty.")

    legacy = _column_map(rows[0])
    layout = None if legacy else _new_layout(rows)
    if not legacy and not layout["line_cols"]:
        raise ValueError(
            "No line columns found — upload the sheet downloaded from this "
            "page, with its heading row intact."
        )
    body_start = 1 if legacy else layout["body_start"]

    f = owner_filter_for_admin(admin)
    all_instruments = await Instrument.find().to_list()
    known = {i.token: i for i in all_instruments}
    # "ROOT:MCX:GOLD" is not an instrument — it stands for every GOLD
    # contract, and borrows the nearest one's tick size and segment.
    roots = {
        rt: _nearest_contract(cs) for rt, cs in group_by_root(all_instruments).items()
    }

    updated = cleared = 0
    errors: list[str] = []
    touched: dict[str, list[Decimal]] = {}

    for row in rows[body_start:]:
        if not row or row[0] in (None, ""):
            continue
        token = str(row[0]).strip()
        if token.lower() in _SETTING_MARKERS:
            continue
        row_symbol: str | None = None
        if is_root_token(token):
            inst = roots.get(token)
            row_symbol = root_display(token)
            if inst is None:
                errors.append(f"{root_display(token)}: no contracts on this platform - skipped")
                continue
        else:
            inst = known.get(token)
            if inst is None:
                errors.append(f"{token}: not an instrument on this platform - skipped")
                continue

        trend: str | None = None
        if legacy:
            entries = _legacy_entries(row, legacy, inst, errors)
        else:
            t_idx = layout["trend_idx"]
            if t_idx is not None and len(row) > t_idx:
                trend = normalize_trend(row[t_idx])
            entries = _line_entries(row, layout, inst, errors)

        n_saved = await _upsert(
            admin, inst, entries, f, trend=trend,
            token=token if row_symbol else None, symbol=row_symbol,
        )
        if n_saved is None:
            continue
        if n_saved:
            updated += 1
            touched[token] = [e.price.to_decimal() for e in entries]
        else:
            cleared += 1

    return {
        "updated": updated,
        "cleared": cleared,
        "errors": errors,
        "warnings": await _offscreen_warnings(touched, known),
    }


async def _upsert(
    admin: User,
    inst: Instrument,
    entries: list[ChartLevelEntry],
    f: dict[str, PydanticObjectId | None],
    trend: str | None = None,
    *,
    token: str | None = None,
    symbol: str | None = None,
) -> bool | None:
    """Write one row's lines. True = saved, False = cleared, None = nothing
    to do. Shared by the Excel import and the inline editor so the two can
    never drift apart.

    `token`/`symbol` name a root row ("ROOT:MCX:GOLD"), which has no
    instrument of its own — `inst` is then the contract it borrows a tick
    size and a segment from.
    """
    key = token or inst.token
    doc = await ChartLevel.find_one(
        ChartLevel.owner_admin_id == f["owner_admin_id"],
        ChartLevel.owner_broker_id == f["owner_broker_id"],
        ChartLevel.token == key,
    )
    if not entries and not trend:
        # Every price blank and no trend = clear this instrument entirely.
        if doc is None:
            return None
        await doc.delete()
        return False
    if doc is None:
        doc = ChartLevel(
            owner_admin_id=f["owner_admin_id"],
            owner_broker_id=f["owner_broker_id"],
            token=key,
            symbol=symbol or inst.symbol,
            segment=str(inst.segment),
        )
    doc.symbol = symbol or inst.symbol
    doc.segment = str(inst.segment)
    doc.levels = entries
    doc.trend = trend
    await doc.save()
    # A trend with no lines is a legitimate row, but it is not an "updated
    # lines" one — report it as cleared so the count still adds up.
    return bool(entries)


# How far from the live price a level has to be before it is almost certainly
# a mistake. A line ten times off isn't "wrong", it is simply drawn where no
# one will ever scroll to — which reads as "the feature does nothing".
_OFFSCREEN_RATIO = Decimal("10")
_OFFSCREEN_MAX_CHECKS = 60


async def _offscreen_warnings(
    touched: dict[str, list[Decimal]], known: dict[str, Instrument]
) -> list[str]:
    """Flag levels that sit nowhere near the instrument's live price.

    This is the whole of the "I uploaded prices and no line appeared" report:
    XAUUSD trades near 4300 and had lines at 63, so they were drawn miles
    below the visible range. Cheap to check, and it names the row to fix.
    """
    tokens = list(touched)[:_OFFSCREEN_MAX_CHECKS]
    if not tokens:
        return []
    from app.services import market_data_service

    try:
        quotes = await market_data_service.get_quotes(tokens)
    except Exception:  # noqa: BLE001
        return []
    out: list[str] = []
    for token, q in zip(tokens, quotes, strict=False):
        try:
            ltp = to_decimal(q.get("ltp") or 0)
        except Exception:  # noqa: BLE001
            continue
        if ltp <= 0:
            continue
        if token in known:
            sym = known[token].symbol
        else:
            sym = root_display(token) if is_root_token(token) else token
        for price in touched[token]:
            if price > ltp * _OFFSCREEN_RATIO or price * _OFFSCREEN_RATIO < ltp:
                out.append(
                    f"{sym}: {price} is far from the live price {ltp} — that line "
                    f"is drawn off-screen. Check the row."
                )
    return out


# ── reads ────────────────────────────────────────────────────────────
def to_dict(doc: ChartLevel, tick: Any = None) -> dict[str, Any]:
    return {
        "token": doc.token,
        "symbol": doc.symbol,
        "segment": doc.segment,
        "trend": doc.trend,
        "levels": [
            {
                # Rounded on the way out as well as in: rows written before the
                # rounding existed still hold Excel's fourteen-digit float.
                "price": float(_round_like_tick(e.price.to_decimal(), tick)),
                "color": e.color,
                "label": e.label,
            }
            for e in doc.levels
        ],
    }


async def list_for_admin(admin: User, segment: str | None = None) -> list[dict[str, Any]]:
    f = owner_filter_for_admin(admin)
    q = ChartLevel.find(
        ChartLevel.owner_admin_id == f["owner_admin_id"],
        ChartLevel.owner_broker_id == f["owner_broker_id"],
    )
    if segment:
        q = q.find(ChartLevel.segment == segment)
    docs = await q.to_list()
    if not docs:
        return []
    tokens = [d.token for d in docs]
    ticks = {
        i.token: i.tick_size
        for i in await Instrument.find({"token": {"$in": tokens}}).to_list()
    }
    # A root row has no instrument of its own: show the nearest contract's
    # tick size and live price, so an off-screen price is still obvious.
    quote_token = {t: t for t in tokens}
    for t in tokens:
        if not is_root_token(t):
            continue
        contracts = await contracts_for_root(t)
        if not contracts:
            continue
        near = _nearest_contract(contracts)
        ticks[t] = near.tick_size
        quote_token[t] = near.token
    # The live price next to the lines is what makes a fat-fingered row
    # obvious — a level ten times off the LTP draws off-screen and reads as
    # "the feature is broken".
    ltps: dict[str, float] = {}
    try:
        from app.services import market_data_service

        quotes = await market_data_service.get_quotes([quote_token[t] for t in tokens])
        for token, q2 in zip(tokens, quotes, strict=False):
            ltps[token] = float(
                _round_like_tick(to_decimal(q2.get("ltp") or 0), ticks.get(token))
            )
    except Exception:  # noqa: BLE001
        pass
    out = []
    for d in docs:
        row = to_dict(d, ticks.get(d.token))
        row["ltp"] = ltps.get(d.token) or None
        out.append(row)
    return out


async def save_levels(
    admin: User,
    token: str,
    levels: list[dict[str, Any]],
    trend: Any = None,
) -> dict[str, Any]:
    """Inline editor: replace one instrument's lines without the Excel trip.

    Same validation and the same writer as the import, so a price typed here
    is rounded and colour-checked exactly like one typed in the sheet.
    """
    row_symbol: str | None = None
    if is_root_token(token):
        contracts = await contracts_for_root(token)
        if not contracts:
            raise ValueError("No contracts on this platform for that underlying.")
        inst = _nearest_contract(contracts)
        row_symbol = root_display(token)
    else:
        inst = await Instrument.find_one(Instrument.token == token)
        if inst is None:
            raise ValueError("Not an instrument on this platform.")
    entries: list[ChartLevelEntry] = []
    for i, lv in enumerate(levels):
        raw = lv.get("price")
        if raw in (None, ""):
            continue
        try:
            clean = raw.replace(",", "").strip() if isinstance(raw, str) else raw
            price = _round_like_tick(to_decimal(clean), inst.tick_size)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Price {i + 1} is not a number.") from exc
        if price <= 0:
            raise ValueError(f"Price {i + 1} must be greater than 0.")
        label = str(lv.get("label") or "").strip() or None
        entries.append(
            ChartLevelEntry(
                price=Decimal128(str(price)),
                color=normalize_color(lv.get("color"), DEFAULT_COLORS[i % len(DEFAULT_COLORS)]),
                label=label,
            )
        )
    saved = await _upsert(
        admin, inst, entries, owner_filter_for_admin(admin), trend=normalize_trend(trend),
        token=token if row_symbol else None, symbol=row_symbol,
    )
    return {"saved": bool(saved), "levels": len(entries)}


async def clear_for_admin(admin: User, token: str) -> bool:
    f = owner_filter_for_admin(admin)
    doc = await ChartLevel.find_one(
        ChartLevel.owner_admin_id == f["owner_admin_id"],
        ChartLevel.owner_broker_id == f["owner_broker_id"],
        ChartLevel.token == token,
    )
    if doc is None:
        return False
    await doc.delete()
    return True


def _owner_cascade(
    user: User, *, include_platform: bool
) -> list[dict[str, PydanticObjectId | None]]:
    """Owners to consult for `user`, closest first: immediate broker → parent
    brokers (tip→root) → assigned admin → platform default.

    ``include_platform`` is the one place the two cascades differ. LINES stop
    at the assigned admin — a sub-admin's users must never be shown the
    platform's levels, same rule as company banks. VISIBILITY does fall
    through to the platform, because "the sub-admin didn't choose" has to
    mean "whatever the super admin said".
    """
    tried: list[dict[str, PydanticObjectId | None]] = []
    if user.assigned_broker_id is not None:
        tried.append({"owner_admin_id": None, "owner_broker_id": user.assigned_broker_id})
    for parent in reversed(list(user.broker_ancestry or [])):
        if parent == user.assigned_broker_id:
            continue
        tried.append({"owner_admin_id": None, "owner_broker_id": parent})
    if user.assigned_admin_id is not None:
        tried.append({"owner_admin_id": user.assigned_admin_id, "owner_broker_id": None})
        if include_platform:
            tried.append({"owner_admin_id": None, "owner_broker_id": None})
    else:
        tried.append({"owner_admin_id": None, "owner_broker_id": None})
    return tried


async def _visibility_row(
    f: dict[str, PydanticObjectId | None],
) -> ChartLevelVisibility | None:
    return await ChartLevelVisibility.find_one(
        ChartLevelVisibility.owner_admin_id == f["owner_admin_id"],
        ChartLevelVisibility.owner_broker_id == f["owner_broker_id"],
    )


async def _resolve_visibility(
    cascade: list[dict[str, PydanticObjectId | None]],
) -> tuple[bool, bool]:
    """Walk owners closest-first and answer (shown, locked).

    The nearest LOCKED row wins outright — a locked row is the super admin's
    decision about that tier, so a broker underneath a blocked sub-admin
    cannot switch their own lines back on. Failing that, the nearest row of
    any kind wins. Nobody has decided anything = shown, which is how the
    feature behaved before the switch existed.
    """
    nearest: ChartLevelVisibility | None = None
    for f in cascade:
        row = await _visibility_row(f)
        if row is None:
            continue
        if row.locked:
            return row.enabled, True
        if nearest is None:
            nearest = row
    return (nearest.enabled if nearest is not None else True), False


def _admin_cascade(admin: User) -> list[dict[str, PydanticObjectId | None]]:
    """The owners that decide what THIS actor's users see, own row first.

    A broker already appears at the head of their own user cascade; a
    sub-admin does not (their users reach them via `assigned_admin_id`), so
    the row is prepended rather than assumed.
    """
    own = owner_filter_for_admin(admin)
    return [own] + [
        f for f in _owner_cascade(admin, include_platform=True) if f != own
    ]


async def visibility_for_user(user: User) -> bool:
    """Should this user see chart lines at all?"""
    shown, _ = await _resolve_visibility(_owner_cascade(user, include_platform=True))
    return shown


async def get_visibility(admin: User) -> dict[str, Any]:
    """What the Chart Lines page shows above the table: this actor's own
    choice (None = following the tier above), what that tier says, the value
    their users actually get, and whether the super admin has pinned it."""
    own = owner_filter_for_admin(admin)
    row = await _visibility_row(own)
    chain = _admin_cascade(admin)
    effective, _ = await _resolve_visibility(chain)
    inherited, locked_above = await _resolve_visibility(chain[1:])
    return {
        "enabled": row.enabled if row is not None else None,
        "inherited": inherited,
        "effective": effective,
        "canInherit": admin.role != UserRole.SUPER_ADMIN,
        # Either my own row is pinned, or a tier above me is — both mean the
        # buttons are read-only for everyone except the super admin.
        "locked": (row.locked if row is not None else False) or locked_above,
        "isSuperAdmin": admin.role == UserRole.SUPER_ADMIN,
    }


async def set_visibility(admin: User, enabled: bool | None) -> dict[str, Any]:
    """`None` deletes this actor's row, which puts them back on the tier
    above — that is the "I haven't chosen" state, not a third stored value."""
    own = owner_filter_for_admin(admin)
    row = await _visibility_row(own)
    if admin.role != UserRole.SUPER_ADMIN:
        current = await get_visibility(admin)
        if current["locked"]:
            raise ValueError(
                "The Super Admin has set this for you — it can't be changed here."
            )
    if enabled is None:
        if row is not None:
            await row.delete()
    elif row is None:
        await ChartLevelVisibility(**own, enabled=enabled).insert()
    else:
        row.enabled = enabled
        # The owner editing their OWN switch releases the pin; only the super
        # admin can hold one, and only the super admin reaches this branch
        # with a locked row in front of them.
        row.locked = row.locked and admin.role == UserRole.SUPER_ADMIN
        await row.save()
    return await get_visibility(admin)


# ── super admin: the switch for one sub-admin or broker ──────────────
def _owner_for(target: User) -> dict[str, PydanticObjectId | None]:
    if target.role == UserRole.BROKER:
        return {"owner_admin_id": None, "owner_broker_id": target.id}
    return {"owner_admin_id": target.id, "owner_broker_id": None}


async def _managed_targets() -> list[User]:
    return await User.find(
        {
            "role": {"$in": [UserRole.ADMIN.value, UserRole.BROKER.value]},
            "status": {"$ne": UserStatus.CLOSED.value},
        }
    ).to_list()


async def list_managed_visibility(admin: User) -> list[dict[str, Any]]:
    """Every sub-admin and broker with the state of their switch.

    This is how the super admin turns chart lines off for one sub-admin's
    whole client pool without touching anybody else's.
    """
    if admin.role != UserRole.SUPER_ADMIN:
        raise ValueError("Only the Super Admin can set this for other tiers.")
    out: list[dict[str, Any]] = []
    for t in sorted(await _managed_targets(), key=lambda u: (u.role, u.full_name or "")):
        own = _owner_for(t)
        row = await _visibility_row(own)
        effective, _ = await _resolve_visibility(_admin_cascade(t))
        out.append(
            {
                "id": str(t.id),
                "name": t.full_name or t.user_code,
                "userCode": t.user_code,
                "role": str(t.role),
                "enabled": row.enabled if row is not None else None,
                # True when the super admin pinned it, so the UI can say who
                # set it — the row alone can't tell you.
                "locked": bool(row is not None and row.locked),
                "effective": effective,
            }
        )
    return out


async def set_visibility_for(
    admin: User, target_id: str, enabled: bool | None
) -> list[dict[str, Any]]:
    """Pin (or release) one sub-admin's / broker's switch. `None` releases it
    and hands control back to that tier."""
    if admin.role != UserRole.SUPER_ADMIN:
        raise ValueError("Only the Super Admin can set this for other tiers.")
    try:
        target = await User.get(PydanticObjectId(target_id))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("No such admin or broker.") from exc
    if target is None or target.role not in (UserRole.ADMIN, UserRole.BROKER):
        raise ValueError("No such admin or broker.")

    own = _owner_for(target)
    row = await _visibility_row(own)
    if enabled is None:
        if row is not None:
            await row.delete()
    elif row is None:
        await ChartLevelVisibility(**own, enabled=enabled, locked=True).insert()
    else:
        row.enabled, row.locked = enabled, True
        await row.save()
    return await list_managed_visibility(admin)


async def resolve_for_user(user: User, token: str) -> dict[str, Any]:
    """What the USER's chart should draw for `token`: the lines and the
    trend. Closest owner in the cascade wins — identical ordering to
    ``crypto_config_service.resolve_for_user``."""
    if not await visibility_for_user(user):
        return {"levels": [], "trend": None}
    tried = _owner_cascade(user, include_platform=False)

    # The chart addresses some instruments by SYMBOL where the catalog keys
    # them by token — crypto is "BTCUSD" on screen and "CRYPTO_BTCUSD" in the
    # collection — so a token-only match silently returned no lines there.
    inst = await Instrument.find_one(Instrument.token == token)
    if inst is None:
        inst = await Instrument.find_one(Instrument.symbol == token)
    tokens = {token}
    if inst is not None:
        tokens.add(inst.token)

    # Lines set on the underlying ("ROOT:MCX:GOLD") cover every expiry of it,
    # so the admin fills GOLD once instead of once per contract. Checked
    # AFTER the exact token within the same owner: a contract that carries
    # its own row still overrides the family's.
    root = root_token_for(inst) if inst is not None else None

    for f in tried:
        for match in (In(ChartLevel.token, list(tokens)),) + (
            (ChartLevel.token == root,) if root else ()
        ):
            doc = await ChartLevel.find_one(
                ChartLevel.owner_admin_id == f["owner_admin_id"],
                ChartLevel.owner_broker_id == f["owner_broker_id"],
                match,
            )
            if doc is not None and (doc.levels or doc.trend):
                full = to_dict(doc, inst.tick_size if inst else None)
                return {"levels": full["levels"], "trend": full["trend"]}
    return {"levels": [], "trend": None}
