"""Checks for the chart-lines Excel round-trip.

The parser is the part worth pinning: a colour that silently falls through to
something invalid reaches TradingView as a black or invisible line with no
error anywhere, and a price column read at the wrong offset would attach a
level to the wrong colour.

    pytest -q backend/tests/test_chart_levels.py
"""

from __future__ import annotations

from app.services.chart_level_service import (
    DEFAULT_COLORS,
    HEADERS,
    MAX_LEVELS,
    normalize_color,
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


def test_header_layout_matches_the_parser_offsets():
    """import_workbook reads price at index 3 + i*3, colour at +1, label at +2.
    If the header ever grows a column, this fails before a live sheet does."""
    assert HEADERS[:3] == ["Token", "Symbol", "Segment"]
    assert len(HEADERS) == 3 + MAX_LEVELS * 3
    for i in range(MAX_LEVELS):
        base = 3 + i * 3
        assert HEADERS[base] == f"Price {i + 1}"
        assert HEADERS[base + 1] == f"Color {i + 1}"
        assert HEADERS[base + 2] == f"Label {i + 1}"


def test_four_default_colors_are_distinct():
    """A sheet filled in without touching the colour columns must still give
    four telling-apart-able lines."""
    assert len(DEFAULT_COLORS) == MAX_LEVELS
    assert len(set(DEFAULT_COLORS)) == MAX_LEVELS
