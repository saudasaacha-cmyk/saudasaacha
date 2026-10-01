"""Credits never clear `settlement_outstanding` — it is informational only.

This file used to assert the opposite: a deposit, a bonus, an admin
adjustment or a margin release would all pay the outstanding down before
touching `available_balance`. That rule was removed deliberately — per the
operator, "balance kabhi negative na ho, user nahi bharega": the field
records what the platform could not recover from a stop-out, and the user is
not liable to top it up out of a later deposit.

Recovery on margin release went the same way, and for a sharper reason: a
race could credit `used_margin` back while `available_balance` lagged, so
the recovery branch booked a phantom outstanding against a wallet that was
not actually short — the CL30479363 incident, where a user ended up with a
healthy balance AND a stranded outstanding at the same time.

The tests below pin the current rule from both sides, so re-introducing the
recovery branch fails here rather than in production.

    pytest -q backend/tests/test_wallet_settlement_outstanding/test_deposit_recovery.py
"""

from decimal import Decimal

import pytest
from bson import Decimal128

from app.models.transaction import TransactionType, WalletTransaction
from app.models.wallet import Wallet
from app.services import wallet_service

# Every credit type that reaches `adjust`. None of them may touch the
# outstanding — listed out so a new one is a deliberate decision.
CREDIT_TYPES = [
    TransactionType.DEPOSIT,
    TransactionType.BONUS,
    TransactionType.ADJUSTMENT,
    TransactionType.REVERSAL,
]


@pytest.mark.asyncio
async def test_deposit_with_no_outstanding_credits_normally(db, user, wallet):
    await wallet_service.adjust(
        user_id=user.id,
        amount=Decimal("2000"),
        transaction_type=TransactionType.DEPOSIT,
        narration="user deposit",
    )
    w = await Wallet.find_one(Wallet.user_id == user.id)
    assert Decimal(str(w.available_balance)) == Decimal("3000")  # 1000 + 2000
    assert Decimal(str(w.settlement_outstanding)) == Decimal("0")


@pytest.mark.asyncio
@pytest.mark.parametrize("txn_type", CREDIT_TYPES)
async def test_a_credit_leaves_the_outstanding_alone(db, user, wallet, txn_type):
    """The whole credit lands in available_balance; the outstanding is
    exactly as it was."""
    wallet.available_balance = Decimal128("0")
    wallet.settlement_outstanding = Decimal128("400")
    await wallet.save()

    await wallet_service.adjust(
        user_id=user.id,
        amount=Decimal("1000"),
        transaction_type=txn_type,
        narration=f"{txn_type.value} credit",
    )
    w = await Wallet.find_one(Wallet.user_id == user.id)
    assert Decimal(str(w.available_balance)) == Decimal("1000")
    assert Decimal(str(w.settlement_outstanding)) == Decimal("400")


@pytest.mark.asyncio
async def test_a_credit_writes_no_recovery_ledger_entry(db, user, wallet):
    """SETTLEMENT_OUTSTANDING_RECOVERY is written when a deposit actually
    pays an outstanding down. Nothing does that any more, so a deposit must
    leave one ledger row and only one."""
    wallet.available_balance = Decimal128("0")
    wallet.settlement_outstanding = Decimal128("400")
    await wallet.save()

    await wallet_service.adjust(
        user_id=user.id,
        amount=Decimal("1000"),
        transaction_type=TransactionType.DEPOSIT,
        narration="user deposit",
    )
    types = [
        t.transaction_type
        for t in await WalletTransaction.find(WalletTransaction.user_id == user.id).to_list()
    ]
    assert types == [TransactionType.DEPOSIT]


@pytest.mark.asyncio
async def test_released_margin_goes_straight_back_to_balance(db, user, wallet):
    """Not into the outstanding first. This is the CL30479363 guard."""
    wallet.available_balance = Decimal128("0")
    wallet.used_margin = Decimal128("3000")
    wallet.settlement_outstanding = Decimal128("1000")
    await wallet.save()

    await wallet_service.release_margin(user.id, Decimal("3000"))

    w = await Wallet.find_one(Wallet.user_id == user.id)
    assert Decimal(str(w.used_margin)) == Decimal("0")
    assert Decimal(str(w.available_balance)) == Decimal("3000")
    assert Decimal(str(w.settlement_outstanding)) == Decimal("1000")


@pytest.mark.asyncio
async def test_release_margin_with_no_outstanding_is_unchanged(db, user, wallet):
    wallet.available_balance = Decimal128("1000")
    wallet.used_margin = Decimal128("500")
    wallet.settlement_outstanding = Decimal128("0")
    await wallet.save()

    await wallet_service.release_margin(user.id, Decimal("500"))

    w = await Wallet.find_one(Wallet.user_id == user.id)
    assert Decimal(str(w.used_margin)) == Decimal("0")
    assert Decimal(str(w.available_balance)) == Decimal("1500")
    assert Decimal(str(w.settlement_outstanding)) == Decimal("0")
