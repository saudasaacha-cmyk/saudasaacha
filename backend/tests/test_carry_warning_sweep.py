"""The pre-close warning reads the gate's own arithmetic, without acting.

`carry_shortfall_by_user` answers "what would each user be short if this
group's close happened now", so a user can still fix it. Its only job is to
agree with `convert_intraday_to_carry`, which is why it borrows
`overnight_settings_for`, `overnight_margin_for` and `carry_shortfall` instead
of restating any of them. A warning the gate then disagrees with is worse than
silence: the user funds the account to the figure they were given and is
force-closed anyway. That exact failure shipped once already.

Two things here are genuinely this module's own and are pinned accordingly:
the exclusions (`carry_requirement_for`), and the algebra that re-expresses a
group-scoped `need` in the shape `carry_shortfall` takes.

    pytest -q backend/tests/test_carry_warning_sweep.py
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.position_service import (
    carry_capacity,
    carry_requirement_for,
    carry_shortfall,
    group_carry_shortfall,
)


def position(locked="1000", opted_in=False, symbol="NIFTY26NOVFUT"):
    return SimpleNamespace(
        quantity=100,
        avg_price=Decimal("500"),
        margin_used=Decimal(locked),
        segment_type="NFO",
        user_carry_forward=opted_in,
        instrument=SimpleNamespace(lot_size=50, segment="NFO", symbol=symbol),
    )


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    """Carryable segment, 1x overnight, INR — so a test's own change is the
    only thing that can move the answer."""
    import app.services.market_data_service as mds
    import app.services.position_service as ps

    monkeypatch.setattr(mds, "is_usd_quoted_segment", lambda _s: False)

    async def _resolve(_pos):
        return {
            "margin_calc_mode": "times",
            "overnight_margin_percentage": 100.0,
            "overnight_leverage": 1.0,
            "overnight_fixed_margin_per_lot": 0,
            "selling_overnight": True,
        }

    monkeypatch.setattr(ps, "overnight_settings_for", _resolve)


# ── exclusions: positions no deposit can save ────────────────────────
async def test_an_ordinary_position_is_counted():
    req = await carry_requirement_for(position(), toggle_on=False)
    assert req == (Decimal("50000.00"), Decimal("1000"))


async def test_the_toggle_being_off_for_the_pool_counts_every_position():
    """Pool never enabled per-position carry, so the platform's normal
    auto-carry runs and `user_carry_forward` is irrelevant."""
    req = await carry_requirement_for(position(opted_in=False), toggle_on=False)
    assert req is not None


async def test_a_position_not_opted_in_is_excluded():
    assert await carry_requirement_for(position(opted_in=False), toggle_on=True) is None


async def test_a_position_opted_in_is_counted():
    assert await carry_requirement_for(position(opted_in=True), toggle_on=True) is not None


async def test_a_segment_that_forbids_overnight_is_excluded(monkeypatch):
    import app.services.position_service as ps

    async def _no_carry(_pos):
        return {"selling_overnight": False, "overnight_leverage": 1.0}

    monkeypatch.setattr(ps, "overnight_settings_for", _no_carry)
    assert await carry_requirement_for(position(), toggle_on=False) is None


async def test_selling_overnight_defaults_to_allowed(monkeypatch):
    """An un-set flag must not silently exclude a whole segment from the
    warning — the gate reads the same default."""
    import app.services.position_service as ps

    async def _unset(_pos):
        return {"overnight_leverage": 1.0}

    monkeypatch.setattr(ps, "overnight_settings_for", _unset)
    assert await carry_requirement_for(position(), toggle_on=False) is not None


# ── the rule the sweep quotes ───────────────────────────────────────
# need, locked, available, floating, credit
CASES = [
    ("410000", "400000", "167072.22", "-300886", "0"),   # the reported account
    ("410000", "400000", "167072.22", "-300886", "50000"),
    ("100000", "0", "100000", "0", "0"),                 # exactly covered
    ("100000", "250000", "10000", "75000", "0"),         # book in profit
    ("1", "0", "0", "0", "0"),                           # one rupee short
    ("0", "900000", "0", "-500000", "0"),                # owes nothing, deep loss
]


def _d(*xs):
    return [Decimal(x) for x in xs]


@pytest.mark.parametrize("need,locked,available,floating,credit", CASES)
def test_the_quote_clears_the_gate_and_not_a_rupee_more(
    need, locked, available, floating, credit
):
    """The whole contract: deposit the quote and `carry_capacity` covers
    `need`; deposit a rupee less and it does not."""
    need, _locked, available, floating, credit = _d(
        need, locked, available, floating, credit
    )
    short = group_carry_shortfall(need, available, floating, credit)

    def capacity(extra):
        return carry_capacity(
            SimpleNamespace(available_balance=available + extra, credit_limit=credit),
            floating,
        )

    assert need <= capacity(short), f"quoted {short}, gate still fails"
    if short > 0:
        assert not (need <= capacity(short - Decimal("1"))), f"over-quoted at {short}"


@pytest.mark.parametrize("need,locked,available,floating,credit", CASES)
def test_the_intraday_lock_never_enters_the_quote(
    need, locked, available, floating, credit
):
    """`need` is already net of the lock. If the lock leaked back in, a user
    with a large intraday position would be quoted a different top-up than an
    identical one with a small lock."""
    need, locked, available, floating, credit = _d(
        need, locked, available, floating, credit
    )
    base = group_carry_shortfall(need, available, floating, credit)
    assert base == group_carry_shortfall(need, available, floating, credit)
    # The sweep's callers differ only in `locked`; it is not even a parameter,
    # so this asserts the signature keeps it that way.
    import inspect

    from app.services.position_service import group_carry_shortfall as g

    assert "locked" not in inspect.signature(g).parameters


def test_owing_nothing_is_never_a_demand():
    """`carry_capacity` floors at zero so a `need` of nothing always passes.
    Quoting the shortfall against capacity anyway billed a user who owed
    nothing for the whole of their floating loss."""
    assert group_carry_shortfall(
        Decimal("0"), Decimal("0"), Decimal("-500000"), Decimal("0")
    ) == 0


def test_an_account_already_covering_its_need_is_asked_for_nothing():
    assert group_carry_shortfall(
        Decimal("100"), Decimal("5000"), Decimal("0"), Decimal("0")
    ) == 0


# ── tied to the user-facing rule ────────────────────────────────────
@pytest.mark.parametrize("need,locked,available,floating,credit", CASES)
def test_it_agrees_with_the_tile_rule_wherever_both_apply(
    need, locked, available, floating, credit
):
    """`carry_shortfall` (what the screens quote, framed as required-vs-equity)
    and `group_carry_shortfall` (what the warning quotes, framed as
    need-vs-capacity) are two readings of one gate. Where both are defined —
    `need > 0` — they must give the same rupees, or the notification and the
    positions screen send a user to two different numbers.
    """
    need, locked, available, floating, credit = _d(
        need, locked, available, floating, credit
    )
    if need <= 0:
        pytest.skip("tile framing has no equivalent when nothing extra is owed")
    assert group_carry_shortfall(need, available, floating, credit) == carry_shortfall(
        need + locked, available + locked + floating, credit
    )
