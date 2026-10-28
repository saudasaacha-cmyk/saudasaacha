"""The overnight carry gate is measured against EQUITY, not cash.

At each segment's close `convert_intraday_to_carry` asks, per user, whether
the account can back the EXTRA margin its whole open book needs overnight
(`need` = the overnight requirement minus the intraday lock). If it cannot,
the worst-loss positions are squared off one at a time until the remainder
fits, and the survivors carry.

What the account can put behind that used to be cash: available + credit. So
a book sitting on a large floating LOSS passed the gate and carried overnight
on money it had already lost on paper, while a book sitting on a floating
PROFIT was squared off despite being worth more than its cash said.

Equity fixes both directions, and the second direction is the one worth
saying out loud: this makes the gate STRICTER for a losing book. That is the
point of it.

    pytest -q backend/tests/test_carry_capacity.py
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.position_service import carry_capacity, convert_intraday_to_carry


def wallet(available: str, credit: str = "0", used: str = "0"):
    """A wallet with just the fields the gate reads."""
    return SimpleNamespace(
        available_balance=Decimal(available),
        credit_limit=Decimal(credit),
        used_margin=Decimal(used),
    )


# ── the rule itself ──────────────────────────────────────────────────
def test_cash_and_credit_still_count():
    assert carry_capacity(wallet("1000", credit="500"), Decimal("0")) == Decimal("1500")


def test_an_open_profit_backs_the_carry():
    """The case the operator asked for: ₹1000 cash and ₹400 running profit
    covers a ₹1300 overnight requirement that cash alone would have failed."""
    assert carry_capacity(wallet("1000"), Decimal("400")) == Decimal("1400")


def test_an_open_loss_stops_backing_it():
    """The other direction, and the one that changes behaviour for real
    users: ₹1000 cash with ₹400 of floating loss backs ₹600, not ₹1000."""
    assert carry_capacity(wallet("1000"), Decimal("-400")) == Decimal("600")


@pytest.mark.parametrize("floating", [None, Decimal("0")])
def test_a_flat_book_is_unchanged(floating):
    """No open P&L ⇒ identical to the old cash-only gate. Most accounts at
    most closes are here, so this is the no-op path."""
    assert carry_capacity(wallet("1000", credit="250"), floating) == Decimal("1250")


def test_used_margin_is_not_counted():
    """`delta` is the overnight requirement MINUS the intraday lock, so the
    locked margin is already netted out of `need`. Adding it here would let
    every carry be backed twice by the same rupees."""
    assert carry_capacity(wallet("1000", used="9999"), Decimal("0")) == Decimal("1000")


def test_capacity_floors_at_zero():
    """A loss bigger than cash + credit would otherwise go negative — and a
    negative capacity fails even `need == 0`, squaring off a book that needs
    no extra margin at all. An account genuinely underwater is the risk
    enforcer's stop-out to handle, not this gate's."""
    assert carry_capacity(wallet("100"), Decimal("-5000")) == Decimal("0")


def test_the_floor_cannot_turn_a_zero_need_into_a_squareoff():
    """The guard this floor exists for, stated as the caller states it."""
    capacity = carry_capacity(wallet("100"), Decimal("-5000"))
    need = Decimal("0")
    assert not (need > capacity), "a book needing nothing extra got closed"


# ── how the caller feeds it ──────────────────────────────────────────
SRC = textwrap.dedent(inspect.getsource(convert_intraday_to_carry))


def test_the_gate_calls_the_rule_rather_than_inlining_it():
    tree = ast.parse(SRC)
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "carry_capacity" in calls


def test_floating_pnl_is_summed_over_the_whole_book_not_one_segment():
    """Equity is a wallet-level quantity. A loss running in MCX is just as
    real against an NFO carry, so the lookup must not be restricted to the
    segment group being rolled — which is what `rows` holds."""
    i = SRC.index("floating_by_user")
    window = SRC[i : SRC.index("for _uid, items in by_user.items():")]
    assert '"user_id": {"$in"' in window, "the floating-P&L query is not per user"
    assert "segment" not in window, "the query was narrowed to the rolled segment"


def test_a_failed_read_falls_back_to_cash_rather_than_to_free_carry():
    """If the floating-P&L lookup throws, the dict stays empty and every
    account is judged on cash alone — stricter than equity for a book in
    profit, identical for a flat one. The dangerous direction would be
    treating an unknown as a credit."""
    i = SRC.index("floating_by_user")
    window = SRC[i : SRC.index("for _uid, items in by_user.items():")]
    assert "except Exception" in window
    assert "floating_by_user = {}" in window
