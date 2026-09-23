"""Per-user script overrides use the same shorthand as the global ones.

Admins type `CRUDEOILFUT` on both Script tabs, because the real contract
name (`CRUDEOIL26OCTFUT`) changes every month. The global layer matched
that shorthand; the per-user layer only matched exact symbols, so every
per-user script override silently did nothing — 19 dead rows in
production, all of them margin overrides somebody thought were live.

    pytest -q backend/tests/test_user_script_override.py
"""

from __future__ import annotations

import pytest
from beanie import PydanticObjectId

from app.services import netting_service as ns

USER = PydanticObjectId()


class _Row:
    def __init__(self, symbol, segment_name="MCX_FUT", **fields):
        self.symbol = symbol
        self.segment_name = segment_name
        self.user_id = USER
        self.isActive = fields.pop("isActive", None)
        self.tradingEnabled = fields.pop("tradingEnabled", None)
        for k, v in fields.items():
            setattr(self, k, v)


@pytest.fixture
def rows(monkeypatch):
    def install(rows):
        class _Q:
            async def to_list(self):
                return rows

        from app.models.netting import UserSegmentOverride

        monkeypatch.setattr(
            UserSegmentOverride, "find", classmethod(lambda cls, *a, **k: _Q())
        )

    return install


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("contract", "expected"),
    [
        ("CRUDEOIL26OCTFUT", "CRUDEOILFUT"),
        ("CRUDEOIL26NOVFUT", "CRUDEOILFUT"),
        ("GOLD26DECFUT", "GOLDFUT"),
        # Mini contract has its OWN row; it must win over the big one
        # because it starts with GOLDM.
        ("GOLDM26DECFUT", "GOLDMFUT"),
    ],
)
async def test_shorthand_covers_every_expiry(rows, contract, expected):
    rows([_Row("CRUDEOILFUT"), _Row("GOLDFUT"), _Row("GOLDMFUT")])
    hit = await ns._match_pattern_user_override(USER, "MCX_FUT", contract)
    assert hit is not None and hit.symbol == expected


@pytest.mark.asyncio
async def test_an_unrelated_contract_matches_nothing(rows):
    rows([_Row("CRUDEOILFUT")])
    assert await ns._match_pattern_user_override(USER, "MCX_FUT", "ZINC26SEPFUT") is None


@pytest.mark.asyncio
async def test_a_full_contract_row_is_not_treated_as_a_pattern(rows):
    """A row naming one contract stays exact — the caller matched it
    already, and it must not spill onto other months."""
    rows([_Row("CRUDEOIL26OCTFUT")])
    assert await ns._match_pattern_user_override(USER, "MCX_FUT", "CRUDEOIL26NOVFUT") is None


@pytest.mark.asyncio
async def test_the_mini_contract_keeps_its_own_margin(rows):
    """GOLDFUT and GOLDMFUT both match GOLDM26DECFUT under start/end —
    and in production they carry Rs 1L vs Rs 3k per lot. The longer base
    has to win regardless of which row Mongo returns first."""
    rows([_Row("GOLDFUT"), _Row("GOLDMFUT")])
    hit = await ns._match_pattern_user_override(USER, "MCX_FUT", "GOLDM26DECFUT")
    assert hit is not None and hit.symbol == "GOLDMFUT"
    # …and the reverse document order must give the same answer.
    rows([_Row("GOLDMFUT"), _Row("GOLDFUT")])
    hit = await ns._match_pattern_user_override(USER, "MCX_FUT", "GOLDM26DECFUT")
    assert hit is not None and hit.symbol == "GOLDMFUT"


@pytest.mark.asyncio
async def test_the_big_contract_is_unaffected(rows):
    rows([_Row("GOLDMFUT"), _Row("GOLDFUT")])
    hit = await ns._match_pattern_user_override(USER, "MCX_FUT", "GOLD26DECFUT")
    assert hit is not None and hit.symbol == "GOLDFUT"


def test_option_shorthand_splits_too():
    assert ns._split_pattern("BANKNIFTYCE") == ("BANKNIFTY", "CE")
    assert ns._split_pattern("CRUDEOILFUT") == ("CRUDEOIL", "FUT")
    # Real contracts carry digits and are never patterns.
    assert ns._split_pattern("CRUDEOIL26OCTFUT") is None
