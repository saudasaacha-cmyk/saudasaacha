"""What a position must lock to survive the night.

`overnight_margin_for` is the number every EOD force-close turns on: the gate
subtracts the intraday lock from it to get `need`, and the pre-close warning
quotes the shortfall that falls out. Until it was extracted it lived inline in
a 174-statement loop and nothing tested it — a mutation that ignored
`overnight_leverage` entirely passed all 41 carry tests.

The trap it exists to avoid is named in its docstring: in Times mode the
settings resolver deliberately leaves the product-aware `leverage` /
`margin_percentage` fields on the INTRADAY value, so reading those instead of
the `overnight_*` triple silently returns the intraday requirement, `delta`
comes out 0, and a book that cannot afford its carry is waved through. That
already happened once in production on an MCX FUT row at 500x intraday / 70x
overnight.

    pytest -q backend/tests/test_overnight_margin.py
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.position_service import overnight_margin_for


def position(qty=100, avg="500", lot_size=50, segment="NFO"):
    return SimpleNamespace(
        quantity=qty,
        avg_price=Decimal(avg),
        segment_type=segment,
        instrument=SimpleNamespace(lot_size=lot_size, segment=segment),
    )


def settings(**kw):
    """Defaults mirror a Times-mode row with the intraday fields set HIGH, so
    any test that accidentally reads them instead of the overnight triple
    comes out obviously wrong rather than coincidentally right."""
    base = {
        "margin_calc_mode": "times",
        "overnight_margin_percentage": 100.0,
        "overnight_leverage": 1.0,
        "overnight_fixed_margin_per_lot": 0,
        # the intraday fields — never to be read by this function
        "leverage": 500.0,
        "margin_percentage": 100.0,
        "fixed_margin_per_lot": 1,
    }
    base.update(kw)
    return base


@pytest.fixture(autouse=True)
def _inr(monkeypatch):
    """INR-quoted and a fixed rate, unless a test says otherwise."""
    import app.services.market_data_service as mds

    monkeypatch.setattr(mds, "is_usd_quoted_segment", lambda _s: False)
    monkeypatch.setattr(mds, "get_usd_inr_rate", lambda: 80.0)


# ── percent / leverage mode ──────────────────────────────────────────
def test_notional_divided_by_overnight_leverage():
    # 100 x 500 = 50,000 notional at 70x overnight
    assert overnight_margin_for(
        position(), settings(overnight_leverage=70.0)
    ) == Decimal("714.29")


def test_overnight_percentage_scales_the_notional():
    assert overnight_margin_for(
        position(), settings(overnight_margin_percentage=20.0)
    ) == Decimal("10000.00")


def test_the_intraday_leverage_is_never_read():
    """The bug this function was extracted to make impossible. Intraday 500x,
    overnight 70x — reading the wrong field gives 100.00 instead of 714.29."""
    out = overnight_margin_for(position(), settings(overnight_leverage=70.0))
    assert out != Decimal("100.00"), "read the intraday 500x, not overnight 70x"
    assert out == Decimal("714.29")


def test_missing_overnight_fields_fall_back_to_full_notional():
    """A segment row with nothing configured must demand the FULL notional,
    not zero — an absent setting is the strict case, never a free carry."""
    s = settings()
    s["overnight_margin_percentage"] = None
    s["overnight_leverage"] = None
    assert overnight_margin_for(position(), s) == Decimal("50000.00")


def test_a_zero_leverage_does_not_divide_by_zero():
    assert overnight_margin_for(
        position(), settings(overnight_leverage=0)
    ) == Decimal("50000.00")


def test_a_leverage_stored_as_the_STRING_zero_is_also_survived():
    """The case the outer `or to_decimal(1)` actually exists for. A numeric 0
    is caught by Python's own truthiness one step earlier, but "0" out of
    Mongo is a non-empty string and therefore TRUE — it reaches `to_decimal`
    and becomes a real zero divisor. Removing that guard passes every test
    that only ever tries the number."""
    assert overnight_margin_for(
        position(), settings(overnight_leverage="0")
    ) == Decimal("50000.00")


# ── fixed-per-lot mode ───────────────────────────────────────────────
def test_fixed_mode_charges_per_lot():
    # 100 qty / lot 50 = 2 lots x 15,000
    assert overnight_margin_for(
        position(),
        settings(margin_calc_mode="fixed", overnight_fixed_margin_per_lot=15000),
    ) == Decimal("30000.00")


def test_fixed_mode_with_no_rate_falls_back_to_percent():
    """`fixed` selected but the per-lot amount never filled in — must not
    return 0 and wave the carry through."""
    assert overnight_margin_for(
        position(),
        settings(margin_calc_mode="fixed", overnight_fixed_margin_per_lot=0),
    ) == Decimal("50000.00")


def test_a_missing_lot_size_does_not_divide_by_zero():
    assert overnight_margin_for(
        position(lot_size=0),
        settings(margin_calc_mode="fixed", overnight_fixed_margin_per_lot=15000),
    ) == Decimal("1500000.00")


def test_a_negative_lot_size_cannot_invert_the_requirement():
    """What `max(1, ...)` is for — `or 1` already handles 0, so only a
    negative reaches it. Without the clamp the division flips sign and the
    position is recorded as FREEING margin overnight."""
    out = overnight_margin_for(
        position(lot_size=-50),
        settings(margin_calc_mode="fixed", overnight_fixed_margin_per_lot=15000),
    )
    assert out > 0, f"negative lot size produced {out}"
    assert out == Decimal("1500000.00")


# ── short positions ──────────────────────────────────────────────────
def test_a_short_locks_the_same_as_the_equivalent_long():
    long_m = overnight_margin_for(position(qty=100), settings(overnight_leverage=70.0))
    short_m = overnight_margin_for(position(qty=-100), settings(overnight_leverage=70.0))
    assert short_m == long_m, "sign of quantity must not change the requirement"


# ── USD-quoted instruments ───────────────────────────────────────────
def test_usd_quoted_margin_is_converted_to_inr(monkeypatch):
    import app.services.market_data_service as mds

    monkeypatch.setattr(mds, "is_usd_quoted_segment", lambda _s: True)
    assert overnight_margin_for(
        position(), settings(overnight_leverage=70.0)
    ) == Decimal("57142.86")


def test_fixed_per_lot_is_already_inr_and_is_not_converted(monkeypatch):
    """Admin enters fixed-per-lot in rupees, so an FX step would multiply a
    rupee figure by the dollar rate — an 80x over-charge."""
    import app.services.market_data_service as mds

    monkeypatch.setattr(mds, "is_usd_quoted_segment", lambda _s: True)
    assert overnight_margin_for(
        position(),
        settings(margin_calc_mode="fixed", overnight_fixed_margin_per_lot=15000),
    ) == Decimal("30000.00")


def test_either_segment_field_marks_it_usd(monkeypatch):
    """`segment_type` and `instrument.segment` disagree on some rows; either
    saying USD is enough, which is how the gate and order validator read it."""
    import app.services.market_data_service as mds

    monkeypatch.setattr(mds, "is_usd_quoted_segment", lambda s: s == "CRYPTO")
    p = position(segment="NFO")
    p.instrument.segment = "CRYPTO"
    assert overnight_margin_for(p, settings(overnight_leverage=70.0)) == Decimal(
        "57142.86"
    )
