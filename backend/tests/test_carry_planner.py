"""The carry-forward plan: carry what the funds cover, cut the oldest first.

Every case here is one the sweep got wrong before it was pulled out into
pure functions — most expensively the brokerage one, where a plan built on
the gross margin came up short by exactly the square's own charge and a
carry the arithmetic had approved failed at execution.

    pytest -q backend/tests/test_carry_planner.py
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal as D

from app.services.carry_planner import (
    affordable_carry,
    carry_step,
    exit_mark,
    overnight_margin,
    plan_carry,
    rollover_fire_time,
)

BOOK = [  # (key, qty, overnight_margin, square_brokerage, step) — oldest first
    ("A", D(100), D(60000), D(1000), D(1)),
    ("B", D(50), D(50000), D(500), D(1)),
    ("C", D(10), D(20000), D(0), D(1)),
]


def test_everything_fits():
    assert plan_carry(BOOK, D(130000)) == {"A": D(100), "B": D(50), "C": D(10)}


def test_trim_oldest_only():
    assert plan_carry(BOOK, D(100000)) == {"A": D(49), "B": D(50), "C": D(10)}


def test_big_shortfall():
    assert plan_carry(BOOK, D(20000)) == {"A": D(0), "B": D(0), "C": D(9)}


def test_brokerage_counted():
    assert plan_carry([("A", D(100), D(60000), D(0), D(1))] + BOOK[1:], D(100000))["A"] == D(50)


def test_profit_keeps_more():
    assert plan_carry(BOOK, D(110000))["A"] > plan_carry(BOOK, D(100000))["A"]


def test_crypto_fraction_step():
    assert plan_carry([("X", D("0.5"), D(10000), D(0), D("0.01"))], D(2345)) == {"X": D("0.11")}


def test_carry_step():
    assert carry_step(0.01, 1) == D("0.01")
    assert carry_step(1, 65) == D(1)
    assert carry_step(0, 1) == D(1)


def test_affordable_carry():
    assert affordable_carry(D(30), D("2401.93"), D("274.38"), D("2730.30"), D(1)) == D(28)
    assert affordable_carry(D(30), D(0), D(10), D(3000), D(1)) == D(0)
    assert affordable_carry(D(30), D(999999), D(0), D(3000), D(1)) == D(29)


def test_exit_mark():
    assert exit_mark(5, {"bid": 99, "ask": 101}) == D(99)
    assert exit_mark(-5, {"bid": 99, "ask": 101}) == D(101)
    assert exit_mark(5, {"bid": 102, "ask": 101}, ltp=100) == D(100)  # crossed book -> ltp
    assert exit_mark(5, {}, None, None, 95) == D(95)  # -> avg


def test_overnight_margin():
    assert overnight_margin({"overnight_margin_percentage": 100, "overnight_leverage": 5}, 10, 100, 1) == D(200)
    assert overnight_margin({"margin_calc_mode": "fixed", "overnight_fixed_margin_per_lot": 5000}, -130, 999, 65) == D(10000)


def test_fire_time():
    assert rollover_fire_time(time(15, 30), 12) == time(15, 42)
    assert rollover_fire_time(time(15, 55), 10) == time(16, 5)
    assert rollover_fire_time(time(23, 55), 10) == time(23, 59)


# ── what the user is told afterwards ─────────────────────────────────
from app.services.carry_planner import carry_outcome_message  # noqa: E402


def test_a_whole_close_names_what_went_and_what_stayed():
    title, body = carry_outcome_message(
        [("ZINC26NOVFUT", D(5000), "CARRY_FORWARD_TRIM", D(5000))],
        [("NIFTY26NOVFUT", D(65))],
        "MCX",
    )
    assert title == "1 position squared off at close"
    assert "Squared off: ZINC26NOVFUT (5000)." in body
    assert "Still carrying: NIFTY26NOVFUT (65)." in body
    assert "oldest" in body


def test_a_partial_says_how_much_is_left():
    """"My gold is gone" and "half my gold is gone" are different messages,
    and the partial exists precisely so the second one is true."""
    title, body = carry_outcome_message(
        [("GOLDM26DECFUT", D(5), "CARRY_FORWARD_PARTIAL", D(10))], [], "MCX"
    )
    assert title == "1 position cut back at close"
    assert "GOLDM26DECFUT (5 of 10)" in body
    assert "the rest still carries" in body


def test_a_long_list_is_summarised_not_dumped():
    cut = [(f"SYM{i}", D(1), "x", D(1)) for i in range(7)]
    _title, body = carry_outcome_message(cut, [], "MCX")
    assert "and 3 more" in body
    assert "SYM6" not in body


def test_quantities_lose_their_decimal_tail():
    _t, body = carry_outcome_message(
        [("BTCUSD", D("0.50"), "x", D("0.50"))], [], "Crypto"
    )
    assert "(0.5)" in body
