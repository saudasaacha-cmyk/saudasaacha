"""The CF shortfall a user is SHOWN must be the deposit that saves them.

`convert_intraday_to_carry` decides at each close whether an account can back
the extra margin its open book needs overnight. Two screens predict that
decision ahead of time — the user app's "CF Extra Needed" tile and the admin
row's `cf_extra_needed` — and when the gate moved to equity neither followed.
Both kept measuring the shortfall against cash, so a book sitting on a
floating LOSS was quoted a top-up smaller than the one that would actually
save it, short by exactly the size of the loss.

What is pinned here is not a formula, it is a relationship: the number on
screen must be the amount which, once deposited, makes the REAL gate pass, and
one rupee less must still fail. Both halves matter — a shortfall that is
merely large enough would pass the first and fail the second, and would train
users to over-fund. Asserting it against the actual `carry_capacity` is the
only reason this test pins anything; a test that restated the formula would
agree with a wrong formula just as happily.

    pytest -q backend/tests/test_carry_shortfall_display.py
"""

from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.position_service import carry_capacity, carry_shortfall


def wallet(available, credit="0"):
    return SimpleNamespace(
        available_balance=Decimal(str(available)), credit_limit=Decimal(str(credit))
    )


def gate_passes(available, credit, floating, cf_required, used) -> bool:
    """The production gate, asked exactly as `convert_intraday_to_carry` asks it:
    `need` (overnight requirement minus the intraday lock) against capacity."""
    need = Decimal(str(cf_required)) - Decimal(str(used))
    return need <= carry_capacity(wallet(available, credit), Decimal(str(floating)))


# ── the relationship ─────────────────────────────────────────────────
# (available, used, floating, credit, cf_required)
BOOKS = [
    # The reported case, to the paisa: balance 5,67,072.22 / used 4,00,000 /
    # M2M -3,00,886 / CF required 8,10,000. Was shown 2,42,927.78.
    ("167072.22", "400000", "-300886", "0", "810000"),
    ("167072.22", "400000", "-300886", "50000", "810000"),  # ...with credit
    ("100000", "50000", "0", "0", "400000"),                # flat book
    ("100000", "50000", "75000", "0", "400000"),            # book in profit
    ("10000", "0", "-9999.99", "0", "250000.01"),           # paisa edges
    ("0", "0", "0", "0", "1"),                              # nothing at all
]


@pytest.mark.parametrize("available,used,floating,credit,cf_required", BOOKS)
def test_the_quoted_deposit_is_exactly_what_makes_the_gate_pass(
    available, used, floating, credit, cf_required
):
    equity = Decimal(available) + Decimal(used) + Decimal(floating)
    short = carry_shortfall(Decimal(cf_required), equity, Decimal(credit))

    topped_up = Decimal(available) + short
    assert gate_passes(topped_up, credit, floating, cf_required, used), (
        f"quoted {short} but the gate still fails after depositing it"
    )

    if short > 0:
        a_rupee_less = topped_up - Decimal("1")
        assert not gate_passes(a_rupee_less, credit, floating, cf_required, used), (
            f"quoted {short} but {short - 1} would already have done — over-quoted"
        )


def test_an_account_that_already_covers_its_carry_is_asked_for_nothing():
    # Equity well past the requirement, so the tile must read zero and green
    # rather than a negative number.
    assert carry_shortfall(Decimal("100"), Decimal("500"), Decimal("0")) == 0
    assert carry_shortfall(Decimal("100"), Decimal("100"), Decimal("0")) == 0


def test_a_floating_loss_raises_the_quote_by_exactly_the_loss():
    """The direction that was wrong in production, stated on its own."""
    flat = carry_shortfall(Decimal("810000"), Decimal("567072.22"), Decimal("0"))
    losing = carry_shortfall(Decimal("810000"), Decimal("266186.22"), Decimal("0"))
    assert losing - flat == Decimal("300886.00")


# ── the user app must ask the same question ──────────────────────────
TILE = Path(__file__).resolve().parents[2] / (
    "frontend-user/app/(dashboard)/positions/page.tsx"
)


@pytest.mark.skipif(not TILE.exists(), reason="user app not in this tree")
def test_the_tile_measures_against_equity_not_balance():
    """The TS copy cannot import the rule, so pin the one line that states it.

    Narrow on purpose: it asserts the shape of the subtraction, not the
    surrounding code, so ordinary edits to the strip do not trip it.
    """
    src = io.open(TILE, encoding="utf-8").read()
    assert "cfRequired - equity - credit" in src, "tile no longer measures against equity"
    assert "cfRequired - balance" not in src, "tile is back to measuring against cash"


# ── the admin row must ask the same question too ─────────────────────
ADMIN = Path(__file__).resolve().parents[1] / "app/api/v1/admin/users.py"


def test_the_admin_row_feeds_equity_into_the_rule():
    """`carry_shortfall` names its parameter `equity`, but a name does not stop
    a caller handing it cash — and a caller handing it cash is precisely the
    bug this whole file exists for. The handler cannot be called without a
    database and an admin session, so read the call site instead of the value.

    Narrow on purpose: only the second argument is asserted, so the endpoint
    can be refactored freely as long as it keeps measuring against equity.
    """
    import ast

    tree = ast.parse(io.open(ADMIN, encoding="utf-8").read())
    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "carry_shortfall"
    ]
    assert len(calls) == 1, f"expected one carry_shortfall call, found {len(calls)}"
    second = calls[0].args[1]
    assert isinstance(second, ast.Name) and second.id == "equity", (
        f"carry_shortfall is being measured against `{ast.unparse(second)}`, not equity"
    )
