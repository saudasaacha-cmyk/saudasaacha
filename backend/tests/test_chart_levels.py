"""Checks for the chart-lines Excel round-trip.

The parser is the part worth pinning: a colour that silently falls through to
something invalid reaches TradingView as a black or invisible line with no
error anywhere, and a price column read at the wrong offset would attach a
level to the wrong colour.

    pytest -q backend/tests/test_chart_levels.py
"""

from __future__ import annotations

from decimal import Decimal

from app.services.chart_level_service import (
    DEFAULT_COLORS,
    DEFAULT_LEVELS,
    FIXED_HEADERS,
    _column_map,
    _new_layout,
    _round_like_tick,
    normalize_color,
    normalize_trend,
)


def test_hex_colors_pass_through_uppercased():
    assert normalize_color("#e31e24", "#000000") == "#E31E24"
    assert normalize_color("#FFF", "#000000") == "#FFF"
    # Bare hex, no leading '#': the operator typed it out of a colour picker.
    assert normalize_color("16A34A", "#000000") == "#16A34A"


def test_color_names_map():
    assert normalize_color("red", "#000000") == "#E31E24"
    assert normalize_color("  Green ", "#000000") == "#16A34A"
    assert normalize_color("BLUE", "#000000") == "#2563EB"


def test_unknown_and_blank_fall_back():
    # Never pass an unrecognised value through — an invalid CSS colour draws a
    # black/invisible line and looks like the feature is broken.
    assert normalize_color("chartreuse-ish", "#123456") == "#123456"
    assert normalize_color("", "#123456") == "#123456"
    assert normalize_color(None, "#123456") == "#123456"
    assert normalize_color("#12345", "#123456") == "#123456"  # 5 digits


def test_header_layout():
    """Token, Symbol, Segment, Trend — then the line columns."""
    assert FIXED_HEADERS == ["Token", "Symbol", "Segment", "Trend"]


def test_default_colors_are_distinct():
    """A sheet filled in without touching the colour row must still give
    lines that can be told apart."""
    assert len(DEFAULT_COLORS) == DEFAULT_LEVELS
    assert len(set(DEFAULT_COLORS)) == DEFAULT_LEVELS


def test_trend_words_operators_actually_type():
    assert normalize_trend("down") == "Downtrend"
    assert normalize_trend("  DOWNTREND ") == "Downtrend"
    assert normalize_trend("Bullish") == "Uptrend"
    assert normalize_trend("side ways") == "Sideways"
    # Unknown is dropped, never stored — the chart chip can't read as garbage.
    assert normalize_trend("dwn") is None
    assert normalize_trend("") is None
    assert normalize_trend(None) is None


# ── the current layout: colour and label set ONCE at the top ─────────
def _sheet(lines=("Line 1", "Line 2", "Line N")):
    """Header + colour row + label row, exactly as the template writes them."""
    return [
        tuple(FIXED_HEADERS) + lines,
        ("Color", None, None, None, "#E31E24", "sky", "#F59E0B"),
        ("Label", None, None, None, "MF", "D1", "DN"),
        ("NATGAS", "NATGAS", "Commodities", "Downtrend", 1, 1.1, 88),
    ]


def test_new_layout_reads_one_colour_and_label_per_column():
    got = _new_layout(_sheet())
    assert got["line_cols"] == [4, 5, 6]
    # "sky" is a name, not hex — it still has to resolve.
    assert got["colors"] == ["#E31E24", "#0EA5E9", "#F59E0B"]
    assert got["labels"] == ["MF", "D1", "DN"]
    assert got["trend_idx"] == 3
    assert got["body_start"] == 3  # data starts at sheet row 4


def test_line_columns_are_positional_not_numbered():
    """'Line N' is the operator's own wording, and the numbering skips — the
    parser must key off POSITION, never the heading text."""
    got = _new_layout(_sheet(lines=("Line 1", "Line 4", "Line N")))
    assert got["line_cols"] == [4, 5, 6]
    assert got["labels"] == ["MF", "D1", "DN"]


def test_colour_and_label_rows_can_be_in_either_order():
    rows = _sheet()
    rows[1], rows[2] = rows[2], rows[1]
    got = _new_layout(rows)
    assert got["colors"] == ["#E31E24", "#0EA5E9", "#F59E0B"]
    assert got["labels"] == ["MF", "D1", "DN"]


def test_setting_rows_may_have_a_blank_token_cell():
    """The operator's own sheet leaves A2 and A3 empty rather than writing
    'Color' / 'Label' in them."""
    rows = _sheet()
    rows[1] = (None,) + rows[1][1:]
    rows[2] = (None,) + rows[2][1:]
    got = _new_layout(rows)
    assert got["body_start"] == 3
    assert got["colors"][0] == "#E31E24"


def test_unfilled_columns_fall_back_to_distinct_defaults():
    """Add a Line column and type nothing in the colour row — the line still
    has to be a different colour from its neighbours."""
    rows = [
        tuple(FIXED_HEADERS) + ("Line 1", "Line 2"),
        ("Color", None, None, None, None, None),
        ("Label", None, None, None, None, None),
    ]
    got = _new_layout(rows)
    assert got["colors"] == DEFAULT_COLORS[:2]
    assert got["labels"] == [None, None]


def test_trailing_spreadsheet_padding_is_not_a_line():
    """Numbers/Excel pad rows out to the sheet width with None. Those columns
    have no heading, no colour and no label — they are not lines."""
    rows = [
        tuple(FIXED_HEADERS) + ("Line 1", None, None),
        ("Color", None, None, None, "#E31E24", None, None),
        ("Label", None, None, None, "MF", None, None),
    ]
    assert _new_layout(rows)["line_cols"] == [4]


def test_the_current_sheet_is_not_mistaken_for_the_old_one():
    """`_column_map` returning {} is what selects the new parser — a sheet
    with no 'Price 1' column must not fall into the legacy path."""
    assert _column_map(tuple(FIXED_HEADERS) + ("Line 1", "Line 2")) == {}


def test_column_map_still_reads_the_old_four_column_sheet():
    """Sheets downloaded before the reorder had Price / Color / Label and only
    four levels. An operator re-uploading one must not have every price land
    in the label."""
    old = ["Token", "Symbol", "Segment"]
    for i in range(1, 5):
        old += [f"Price {i}", f"Color {i}", f"Label {i}"]
    cols = _column_map(tuple(old))
    assert len(cols) == 4
    assert cols[0] == {"price": 3, "color": 4, "label": 5}
    assert cols[3]["price"] == 12


def test_column_map_ignores_a_sheet_that_is_not_ours():
    assert _column_map(("Name", "Qty", "Rate")) == {}
    # A colour column with no matching price is not a level.
    assert _column_map(("Token", "Colour 1")) == {}


def test_price_is_trimmed_to_the_tick_precision_not_snapped_to_a_tick():
    """Excel hands back a formula's cached float, so 4249.17 arrives as
    4249.17065447777. Trim the tail — but never move the operator's price to
    the nearest tick multiple."""
    assert _round_like_tick(Decimal("4249.17065447777"), Decimal("0.05")) == Decimal("4249.17")
    assert _round_like_tick(Decimal("65.69661920027963"), Decimal("0.01")) == Decimal("65.7")
    # Crypto keeps its precision.
    assert _round_like_tick(
        Decimal("0.000012345678901"), Decimal("0.00000001")
    ) == Decimal("0.00001235")
    # Whole numbers stay whole (normalize() would give 1E+2).
    assert str(_round_like_tick(Decimal("100.00"), Decimal("0.05"))) == "100"
    # No tick on the instrument: fall back to paise.
    assert _round_like_tick(Decimal("1253.4567"), None) == Decimal("1253.46")


# ── one row for every expiry of the same underlying ──────────────────
from datetime import UTC, datetime, timedelta  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from app.services.chart_level_service import (  # noqa: E402
    _nearest_contract,
    group_by_root,
    is_root_token,
    root_display,
    root_token_for,
    symbol_root,
)


def _inst(symbol: str, exchange: str = "MCX", expiry=None):
    return SimpleNamespace(token=symbol, symbol=symbol, exchange=exchange, expiry=expiry)


def test_every_expiry_of_a_future_shares_one_root():
    assert symbol_root("GOLD26OCTFUT") == "GOLD"
    assert symbol_root("GOLD26DECFUT") == "GOLD"
    assert symbol_root("GOLD27FEBFUT") == "GOLD"
    # A different contract family is a different root.
    assert symbol_root("GOLDM26OCTFUT") == "GOLDM"
    assert symbol_root("SILVER26DECFUT") == "SILVER"
    # Punctuated underlyings survive.
    assert symbol_root("M&MFIN26OCTFUT") == "M&MFIN"


def test_options_and_cash_have_no_root():
    """A strike is part of an option's identity — 22600 CE and 23000 PE share
    an underlying but not a price range, so one set of lines across them
    would be meaningless."""
    assert symbol_root("NIFTY2691522600CE") is None
    assert symbol_root("SENSEX2691773400PE") is None
    assert symbol_root("RELIANCE") is None
    assert symbol_root("BTCUSD") is None
    assert symbol_root("MCXGOLD") is None  # placeholder, no expiry in the name


def test_root_token_is_scoped_by_exchange():
    assert root_token_for(_inst("GOLD26OCTFUT")) == "ROOT:MCX:GOLD"
    assert root_token_for(_inst("NIFTY26OCTFUT", "NFO")) == "ROOT:NFO:NIFTY"
    assert root_token_for(_inst("RELIANCE", "NSE")) is None
    assert is_root_token("ROOT:MCX:GOLD")
    assert not is_root_token("123668231")
    assert root_display("ROOT:MCX:GOLD").startswith("GOLD")


def test_group_by_root_collects_the_whole_family():
    rows = [_inst("GOLD26OCTFUT"), _inst("GOLD26DECFUT"), _inst("SILVER26DECFUT")]
    groups = group_by_root(rows)
    assert sorted(groups) == ["ROOT:MCX:GOLD", "ROOT:MCX:SILVER"]
    assert len(groups["ROOT:MCX:GOLD"]) == 2


def test_nearest_contract_is_the_front_month():
    """The root row borrows this contract's tick size and live price."""
    now = datetime.now(UTC).replace(tzinfo=None)
    past = _inst("GOLD26SEPFUT", expiry=now - timedelta(days=5))
    near = _inst("GOLD26OCTFUT", expiry=now + timedelta(days=20))
    far = _inst("GOLD27FEBFUT", expiry=now + timedelta(days=140))
    assert _nearest_contract([far, past, near]).symbol == "GOLD26OCTFUT"
    # All expired → the last one, never a crash.
    assert _nearest_contract([past]).symbol == "GOLD26SEPFUT"
    # No expiry dates at all (MCX placeholders) → still returns something.
    assert _nearest_contract([_inst("GOLD26OCTFUT")]).symbol == "GOLD26OCTFUT"
    # Some rows carry a plain `date`, others an aware datetime — both sort.
    from datetime import date, timezone

    mixed = [
        _inst("GOLD26OCTFUT", expiry=date(now.year + 1, 1, 5)),
        _inst("GOLD26DECFUT", expiry=(now + timedelta(days=2)).replace(tzinfo=timezone.utc)),
    ]
    assert _nearest_contract(mixed).symbol == "GOLD26DECFUT"
