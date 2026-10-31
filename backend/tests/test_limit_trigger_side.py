"""A parked LIMIT fires on LTP, from the side its ACTION implies.

The operator's rule, in their words: "If buy is standing as limit order
then LTP or LESS price should only trigger buy and vice versa for sell."

    BUY  LIMIT at P  →  fires once LTP ≤ P
    SELL LIMIT at P  →  fires once LTP ≥ P

...regardless of where P sat relative to the market when the order was
placed. That last clause IS the change. The engine used to capture the
side at placement (`Order.limit_wait_up`) and then wait for the price to
reach the level from that side — so a BUY limit placed ABOVE market
waited for the price to RISE, the exact inverse of the rule above. It
never raised and never logged; the order simply sat while the operator
watched the price trade through it.

A BUY LIMIT above market is therefore marketable and fires on the next
poll. That is standard exchange behaviour and is intended here: the
"wait until price reaches X" order is SL-M, not LIMIT.

SL-M and SL semantics are deliberately unchanged, and are pinned below so
this change can't quietly take them with it.

    pytest -q backend/tests/test_limit_trigger_side.py
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import pytest

from app.models._base import OrderAction, OrderType
from app.services.matching_engine import _should_fill, trigger_pending_orders


def fires(action: OrderAction, ltp: str, limit: str = "0", trigger: str = "0",
          order_type: OrderType = OrderType.LIMIT) -> bool:
    return _should_fill(
        order_type, action, Decimal(ltp), Decimal(limit), Decimal(trigger)
    )


BUY, SELL = OrderAction.BUY, OrderAction.SELL


# ── the rule itself ──────────────────────────────────────────────────
@pytest.mark.parametrize("ltp", ["99", "100"])
def test_buy_fires_at_or_below_its_limit(ltp):
    """"LTP or LESS price should only trigger buy" — inclusive at the touch."""
    assert fires(BUY, ltp, limit="100")


def test_buy_does_not_fire_above_its_limit():
    assert not fires(BUY, "100.01", limit="100")


@pytest.mark.parametrize("ltp", ["100", "101"])
def test_sell_fires_at_or_above_its_limit(ltp):
    assert fires(SELL, ltp, limit="100")


def test_sell_does_not_fire_below_its_limit():
    assert not fires(SELL, "99.99", limit="100")


# ── the half that used to be inverted ────────────────────────────────
def test_a_buy_limit_above_market_is_marketable():
    """Placed at 110 with the market at 100: LTP ≤ 110 already holds, so it
    fires on the next poll. Under the old placement-side capture this order
    waited for the price to climb to 110 instead."""
    assert fires(BUY, "100", limit="110")


def test_a_sell_limit_below_market_is_marketable():
    assert fires(SELL, "100", limit="90")


def test_the_placement_side_is_no_longer_an_input():
    """`limit_wait_up` was the 6th parameter. Dropping it is what makes the
    rule unconditional — if it ever comes back as an argument, the
    inversion comes back with it."""
    params = list(inspect.signature(_should_fill).parameters)
    assert "limit_wait_up" not in params
    assert len(params) == 5


def test_the_poller_does_not_read_the_stored_flag_either():
    """Belt and braces: the column still exists for old rows, so the poller
    could keep passing it."""
    assert "limit_wait_up" not in inspect.getsource(trigger_pending_orders)


# ── guards ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("action", [BUY, SELL])
@pytest.mark.parametrize("limit", ["0", "-5"])
def test_an_unset_limit_never_fires(action, limit):
    """A BUY with limit 0 would otherwise fire on every tick, since
    `ltp <= 0` is... false — but `0 <= ltp` for SELL is always true. The
    explicit guard is what stops the SELL side booking a phantom fill."""
    assert not fires(action, "100", limit=limit)


def test_the_trigger_runs_on_ltp_not_on_bid_or_ask():
    """The poller's price source. `get_ltp_instant` reads the same `_state`
    the user's chart renders from; a switch to a quote's bid/ask would make
    the fill fire half a spread away from what the operator sees."""
    src = inspect.getsource(trigger_pending_orders)
    assert "get_ltp_instant" in src
    assert '"bid"' not in src and '"ask"' not in src


# ── untouched neighbours ─────────────────────────────────────────────
def test_sl_m_still_breaks_out_and_stops_out():
    """BUY SL-M is a stop-BUY (fires as price rises); SELL SL-M is a
    stop-loss exit (fires as price falls). Note this is the OPPOSITE of the
    LIMIT rule above — that asymmetry is the point of having both."""
    assert fires(BUY, "100", trigger="100", order_type=OrderType.SL_M)
    assert not fires(BUY, "99.99", trigger="100", order_type=OrderType.SL_M)
    assert fires(SELL, "100", trigger="100", order_type=OrderType.SL_M)
    assert not fires(SELL, "100.01", trigger="100", order_type=OrderType.SL_M)


def test_sl_still_needs_both_armed_and_inside_its_limit():
    """Stop-LIMIT: armed at the trigger, but protected by the limit, so a
    gap straight PAST the limit does not fill."""
    sl = OrderType.SL
    assert fires(BUY, "101", limit="105", trigger="100", order_type=sl)
    assert not fires(BUY, "99", limit="105", trigger="100", order_type=sl)
    assert not fires(BUY, "106", limit="105", trigger="100", order_type=sl)
    assert fires(SELL, "99", limit="95", trigger="100", order_type=sl)
    assert not fires(SELL, "94", limit="95", trigger="100", order_type=sl)


def test_market_orders_are_not_this_function_s_business():
    assert not fires(BUY, "100", limit="100", order_type=OrderType.MARKET)


# ── the limit-away band: one percentage, two opposite jobs ───────────
# `limitAwayPercent` caps how FAR from market a parked price may rest
# (entry leg) and how CLOSE to entry a bracket may sit (SL / TP). Those
# are opposite comparisons, and the panel once ran the entry leg as a
# minimum while the server ran it as a maximum — the two accepted sets
# met only at the boundary, so any non-zero setting refused almost every
# parked order from one side or the other. It stayed hidden because the
# field has no admin form and defaults to 0, switching both checks off.
# These pin the direction on each side of the wire so it cannot drift
# back.
import pathlib  # noqa: E402
import re  # noqa: E402

from app.services.order_validator import validate  # noqa: E402

VALIDATOR_SRC = inspect.getsource(validate)
PANEL_SRC = (
    pathlib.Path(__file__).resolve().parents[2]
    / "frontend-user"
    / "components"
    / "trading"
    / "OrderPanel.tsx"
).read_text()


def _body(src: str, start: str, end: str) -> str:
    i = src.index(start)
    return src[i : src.index(end, i)]


def test_the_server_treats_the_entry_band_as_a_maximum():
    """Outside ±pct is rejected. `_check_entry` is the entry leg."""
    body = _body(VALIDATOR_SRC, "def _check_entry", "def _check_sl_tp")
    assert "if candidate < lower or candidate > upper:" in body


def test_the_server_treats_the_bracket_band_as_a_minimum():
    """Inside the band is rejected — a stop glued to entry. Opposite of
    the entry leg, deliberately."""
    body = _body(VALIDATOR_SRC, "def _check_sl_tp", "entry_ref = ltp")
    assert "if lower < candidate < upper:" in body


def test_the_panel_agrees_with_the_server_on_the_entry_band():
    """Same direction, and symmetric, so neither side can accept a price
    the other refuses."""
    i = PANEL_SRC.index("const upperCap")
    body = PANEL_SRC[i : PANEL_SRC.index("return;", i)]
    assert "candidate < lowerCap || candidate > upperCap" in body
    assert "too far from market" in body
    assert "too close to market" not in body


def test_the_entry_band_is_measured_from_ltp_on_both_sides():
    """Not from the close-side quote — half a spread of drift between the
    price on the chart and the price the band is drawn around."""
    assert "entry_ref = ltp" in VALIDATOR_SRC
    assert re.search(r"const limitEntryRef = ltp;", PANEL_SRC)


def test_the_field_is_off_by_default():
    """Both checks are gated on > 0, and the seeded default is 0. If this
    ever ships non-zero by default it silently starts refusing orders."""
    seed = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "models" / "netting.py"
    ).read_text()
    assert "limitAwayPercent: float = 0.0" in seed
    assert "if limit_pct > 0 and ltp > 0:" in VALIDATOR_SRC
    assert "if (limitAwayPct > 0 && limitEntryRef > 0" in PANEL_SRC
