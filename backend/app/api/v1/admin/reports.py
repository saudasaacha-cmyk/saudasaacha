"""Admin reports — users, financial, trades, tax, compliance, tradebook PDF."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentAdmin, require_perm, scoped_user_ids
from app.models.order import Order, OrderStatus
from app.models.position import Position, PositionStatus
from app.models.trade import Trade
from app.models.transaction import (
    DepositRequest,
    DepositStatus,
    TransactionType,
    WalletTransaction,
    WithdrawalRequest,
    WithdrawalStatus,
)
from app.models.user import User, UserRole, UserStatus
from app.models.wallet import Wallet
from app.schemas.common import APIResponse
from app.services import report_pdf_service
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["admin-reports"])


@router.get("/users", response_model=APIResponse[dict])
async def users_report(
    admin: CurrentAdmin,
    _: None = Depends(require_perm("reports", "read")),
):
    scope = await scoped_user_ids(admin)
    if not scope:
        return APIResponse(
            data={"total": 0, "active": 0, "blocked": 0, "by_role": {}, "last_24h_signups": 0}
        )
    base = {"_id": {"$in": scope}}
    total = await User.find(base).count()
    active = await User.find({**base, "status": UserStatus.ACTIVE.value}).count()
    blocked = await User.find({**base, "status": UserStatus.BLOCKED.value}).count()
    by_role: dict[str, int] = {}
    for r in UserRole:
        by_role[r.value] = await User.find({**base, "role": r.value}).count()
    yesterday = now_utc() - timedelta(days=1)
    last_24h_signups = await User.find({**base, "created_at": {"$gte": yesterday}}).count()
    return APIResponse(
        data={"total": total, "active": active, "blocked": blocked, "by_role": by_role, "last_24h_signups": last_24h_signups}
    )


@router.get("/financial", response_model=APIResponse[dict])
async def financial_report(
    admin: CurrentAdmin,
    _: None = Depends(require_perm("reports", "read")),
):
    scope = await scoped_user_ids(admin)
    if not scope:
        return APIResponse(
            data={
                "wallet_balance": 0.0,
                "margin_used": 0.0,
                "credit_limit": 0.0,
                "total_deposits": 0.0,
                "total_withdrawals": 0.0,
                "total_brokerage": 0.0,
                "pending_deposits": 0,
                "pending_withdrawals": 0,
            }
        )
    user_q = {"user_id": {"$in": scope}}
    wallets = await Wallet.find(user_q).to_list()
    total_balance = sum(float(str(w.available_balance)) for w in wallets)
    total_used = sum(float(str(w.used_margin)) for w in wallets)
    total_credit = sum(float(str(w.credit_limit)) for w in wallets)
    total_deposits = sum(float(str(w.total_deposits)) for w in wallets)
    total_withdrawals = sum(float(str(w.total_withdrawals)) for w in wallets)
    total_brokerage = sum(float(str(w.total_brokerage)) for w in wallets)

    pending_dep = await DepositRequest.find(
        {"status": DepositStatus.PENDING.value, **user_q}
    ).count()
    pending_wd = await WithdrawalRequest.find(
        {"status": WithdrawalStatus.PENDING.value, **user_q}
    ).count()

    return APIResponse(
        data={
            "wallet_balance": round(total_balance, 2),
            "margin_used": round(total_used, 2),
            "credit_limit": round(total_credit, 2),
            "total_deposits": round(total_deposits, 2),
            "total_withdrawals": round(total_withdrawals, 2),
            "total_brokerage": round(total_brokerage, 2),
            "pending_deposits": pending_dep,
            "pending_withdrawals": pending_wd,
        }
    )


@router.get("/trades", response_model=APIResponse[dict])
async def trades_report(
    admin: CurrentAdmin,
    _: None = Depends(require_perm("reports", "read")),
):
    today = now_utc() - timedelta(hours=24)
    week = now_utc() - timedelta(days=7)
    scope = await scoped_user_ids(admin)
    if not scope:
        empty = {"count": 0, "volume": 0.0, "brokerage": 0.0, "charges": 0.0}
        return APIResponse(data={"today": empty, "week": empty})
    base = {"user_id": {"$in": scope}}
    today_trades = await Trade.find({**base, "executed_at": {"$gte": today}}).to_list()
    week_trades = await Trade.find({**base, "executed_at": {"$gte": week}}).to_list()

    def _agg(rows):
        return {
            "count": len(rows),
            "volume": round(sum(float(str(t.value)) for t in rows), 2),
            "brokerage": round(sum(float(str(t.brokerage)) for t in rows), 2),
            "charges": round(sum(float(str(t.total_charges)) for t in rows), 2),
        }

    return APIResponse(data={"today": _agg(today_trades), "week": _agg(week_trades)})


@router.get("/compliance", response_model=APIResponse[dict])
async def compliance_report(
    admin: CurrentAdmin,
    _: None = Depends(require_perm("reports", "read")),
):
    scope = await scoped_user_ids(admin)
    if not scope:
        return APIResponse(data={"kyc_verified": 0, "kyc_pending": 0})
    base = {"_id": {"$in": scope}}
    kyc_done = await User.find({**base, "kyc.is_verified": True}).count()
    kyc_pending = await User.find({**base, "kyc.is_verified": False}).count()
    return APIResponse(data={"kyc_verified": kyc_done, "kyc_pending": kyc_pending})


# ── Tradebook PDF (ARK Trader style, per-user) ────────────────────


def _d128(v: Any) -> float:
    if v is None:
        return 0.0
    return float(str(v))


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_dt_short(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


@router.get("/tradebook/pdf")
async def tradebook_pdf(
    user_id: str,
    admin: CurrentAdmin,
    _: None = Depends(require_perm("reports", "read")),
    from_date: datetime | None = None,
    to_date: datetime | None = None,
):
    uid = PydanticObjectId(user_id)
    scope = await scoped_user_ids(admin)
    if uid not in scope:
        from app.core.exceptions import InsufficientPermissionsError
        raise InsufficientPermissionsError("User not in your scope")

    user = await User.get(uid)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User not found")

    now = now_utc()
    q_time: dict[str, Any] = {}
    if from_date:
        q_time["$gte"] = from_date
    if to_date:
        q_time["$lte"] = to_date

    # ── 1. Closed transactions (trades + money movements) ──────
    trade_q: dict[str, Any] = {"user_id": uid}
    if q_time:
        trade_q["executed_at"] = q_time
    trades = await Trade.find(trade_q).sort("+executed_at").to_list()

    tx_q: dict[str, Any] = {
        "user_id": uid,
        "transaction_type": {"$in": [
            TransactionType.DEPOSIT.value,
            TransactionType.WITHDRAWAL.value,
            TransactionType.ADJUSTMENT.value,
            TransactionType.BONUS.value,
        ]},
    }
    if q_time:
        tx_q["created_at"] = q_time
    money_txs = await WalletTransaction.find(tx_q).sort("+created_at").to_list()

    # Closed rows come from the SAME FIFO reconstruction the user's app Closed
    # tab renders (and the user's own Full Tradebook PDF), so the admin-side
    # download matches the user's tradebook AND their Closed tab entry-by-entry.
    from app.services.tradebook_builder import fifo_closed_rows

    closed_rows, _fifo_net_pnl, sum_brokerage_from_trades = await fifo_closed_rows(
        uid, from_date, to_date
    )

    for tx in money_txs:
        amt = _d128(tx.amount)
        tx_type_label = tx.transaction_type.value.title()
        closed_rows.append({
            "time": _fmt_dt(tx.created_at),
            "type": "Money",
            "ticket_id": str(tx.id)[-8:] if tx.id else "",
            "script": "",
            "amount": "",
            "type_detail": tx_type_label,
            "open_time": "",
            "open_price": "",
            "close_price": "",
            "dp_wd_aj": f"{amt:,.2f}",
            "brokerage": 0,
            "commission": 0,
            "open_com": 0,
            "total_pnl": 0,
            "comment": tx.narration[:20] if tx.narration else "",
        })

    closed_rows.sort(key=lambda r: r.get("time", ""))

    # ── 2. Money totals ────────────────────────────────────────
    all_tx_q: dict[str, Any] = {"user_id": uid}
    if q_time:
        all_tx_q["created_at"] = q_time
    all_txs = await WalletTransaction.find(all_tx_q).to_list()

    deposit_total = sum(_d128(t.amount) for t in all_txs if t.transaction_type == TransactionType.DEPOSIT)
    withdraw_total = sum(_d128(t.amount) for t in all_txs if t.transaction_type == TransactionType.WITHDRAWAL)
    adjustment_total = sum(_d128(t.amount) for t in all_txs if t.transaction_type == TransactionType.ADJUSTMENT)
    bonus_total = sum(_d128(t.amount) for t in all_txs if t.transaction_type == TransactionType.BONUS)

    money_totals = {
        "credit_in": 0.0,
        "credit_out": 0.0,
        "deposit": deposit_total,
        "withdraw": withdraw_total,
        "adjustment": adjustment_total,
        "bonus": bonus_total,
    }

    # ── 3. Opened deals (open positions) ───────────────────────
    open_positions = await Position.find(
        {"user_id": uid, "status": PositionStatus.OPEN.value}
    ).to_list()

    opened_deals: list[dict[str, Any]] = []
    for p in open_positions:
        qty = abs(p.quantity)
        avg = _d128(p.avg_price)
        ltp = _d128(p.ltp)
        margin = _d128(p.margin_used)
        unrealized = _d128(p.unrealized_pnl)
        sl = _d128(p.stop_loss) if p.stop_loss else 0
        tp = _d128(p.target) if p.target else 0
        side = (p.opened_side.value if p.opened_side else ("Buy" if p.quantity > 0 else "Sell"))
        lot_size = p.instrument.lot_size or 1
        value = qty * ltp * lot_size

        opened_deals.append({
            "ticket_id": str(p.id)[-8:] if p.id else "",
            "time": _fmt_dt(p.opened_at if hasattr(p, "opened_at") and p.opened_at else p.created_at),
            "type_detail": side,
            "amount": f"{qty:,.2f}",
            "script": p.instrument.symbol,
            "price": f"{avg:,.2f}",
            "sl": f"{sl:,.2f}" if sl else "",
            "tp": f"{tp:,.2f}" if tp else "",
            "current_price": f"{ltp:,.2f}",
            "commission": _d128(p.margin_used) * 0,
            "total_pnl": unrealized,
            "value": value,
            "comment": "",
        })

    # ── 4. Pending orders ──────────────────────────────────────
    pending_orders_db = await Order.find({
        "user_id": uid,
        "status": {"$in": [OrderStatus.PENDING.value, OrderStatus.OPEN.value]},
    }).to_list()

    pending_orders: list[dict[str, Any]] = []
    for o in pending_orders_db:
        sl = _d128(o.bracket_stop_loss) if o.bracket_stop_loss else 0
        tp = _d128(o.bracket_target) if o.bracket_target else 0
        pending_orders.append({
            "order_id": o.order_number,
            "type": "SLTP" if (o.order_type.value in ("SL", "SL_M")) else o.order_type.value,
            "type_detail": "SL/TP" if (o.order_type.value in ("SL", "SL_M")) else o.action.value,
            "amount": f"{o.quantity:,.2f}",
            "script": o.instrument.symbol,
            "price": f"{_d128(o.price):,.2f}" if o.price else "",
            "sl": f"{sl:,.2f}" if sl else "",
            "tp": f"{tp:,.2f}" if tp else "",
            "time": _fmt_dt(o.created_at),
            "comment": "",
        })

    # ── 5. Financial standings ─────────────────────────────────
    wallet = await Wallet.find_one({"user_id": uid})
    balance = _d128(wallet.available_balance) if wallet else 0
    used_margin = _d128(wallet.used_margin) if wallet else 0
    credit = _d128(wallet.credit_limit) if wallet else 0
    realized = _d128(wallet.realized_pnl) if wallet else 0
    unrealized_w = _d128(wallet.unrealized_pnl) if wallet else 0

    open_pnl = sum(d.get("total_pnl", 0) for d in opened_deals)
    equity = balance + used_margin + open_pnl
    free_margin = equity - used_margin
    margin_level = (equity / used_margin * 100) if used_margin > 0 else 0

    financial = {
        "balance": balance,
        "credit": credit,
        "equity": round(equity, 2),
        "total_pnl": round(open_pnl, 2),
        "used_margin": used_margin,
        "holding_margin": used_margin,
        "free_margin": round(free_margin, 2),
        "margin_level": f"{margin_level:.2f}%",
    }

    # ── 6. Brokerage total + admin branding ──────────────────
    total_brokerage = sum_brokerage_from_trades

    admin_brand_name = ""
    if admin.brand_name:
        admin_brand_name = admin.brand_name
    elif hasattr(admin, "full_name") and admin.full_name:
        admin_brand_name = admin.full_name

    # ── Assemble payload ───────────────────────────────────────
    from_label = from_date.strftime("%Y-%m-%d") if from_date else "Beginning"
    to_label = to_date.strftime("%Y-%m-%d") if to_date else "Now"

    payload = {
        "from_label": from_label,
        "to_label": to_label,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "closed_transactions": closed_rows,
        "money_totals": money_totals,
        "opened_deals": opened_deals,
        "pending_orders": pending_orders,
        "financial": financial,
        "total_brokerage": total_brokerage,
        "admin_brand_name": admin_brand_name,
    }

    pdf_bytes = report_pdf_service.build_full_tradebook_pdf(user, payload)
    stamp = now.strftime("%Y%m%d")
    user_name = (getattr(user, "full_name", "") or "").strip().replace(" ", "_")
    code = getattr(user, "user_code", "") or "user"
    admin_name = (admin_brand_name or getattr(admin, "full_name", "") or "").strip().replace(" ", "_")
    filename = f"tradebook_{user_name}_{code}_{admin_name}_{stamp}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/top-movers")
async def top_movers(
    admin: CurrentAdmin,
    days: int = Query(default=1, ge=1, le=365, description="Window for the client ranking"),
    limit: int = Query(default=10, ge=1, le=50),
    include_options: bool = Query(
        default=False,
        description="Options swing tens of percent daily and swamp the ranking; off by default",
    ),
    _: None = Depends(require_perm("reports", "read")),
) -> APIResponse[Any]:
    """Two rankings: instruments by live % change, and clients by realised P&L.

    Symbols come from the feed leader's `mdlive` snapshots — that is exactly
    the set of instruments actually streaming, so nothing here invents a price
    for a symbol nobody is watching. Clients are ranked on realised P&L only
    (open trades are not marked here), which keeps one comparable rupee figure.
    """
    from app.core.redis_client import get_redis
    from app.models.instrument import Instrument

    # ── Symbols: scan the live snapshots the feed leader publishes ──────
    gainers: list[dict[str, Any]] = []
    losers: list[dict[str, Any]] = []
    try:
        redis = get_redis()
        keys: list[str] = []
        cursor = 0
        # Bounded scan: the live universe is watchlist-sized, and an admin
        # page must never hold Redis for an unbounded sweep.
        while len(keys) < 5000:
            cursor, batch = await redis.scan(cursor, match="mdlive:*", count=500)
            keys.extend(k.decode() if isinstance(k, bytes) else k for k in batch)
            if cursor == 0:
                break
        quotes: list[dict[str, Any]] = []
        if keys:
            raw_values = await redis.mget(keys)
            for key, raw in zip(keys, raw_values, strict=False):
                if not raw:
                    continue
                try:
                    q = json.loads(raw)
                except Exception:
                    continue
                try:
                    ltp = float(q.get("ltp") or 0)
                    change_pct = float(q.get("change_pct") or 0)
                except (TypeError, ValueError):
                    continue
                if ltp <= 0 or change_pct == 0:
                    continue  # cold or never-moved token: not a mover
                quotes.append(
                    {
                        "token": key.split(":", 1)[1],
                        "ltp": round(ltp, 4),
                        "change_pct": round(change_pct, 2),
                        "change": round(float(q.get("change") or 0), 4),
                    }
                )
        # Name every live token in one query, then rank. Done before the
        # sort because the segment decides whether a row belongs here at all:
        # a far-OTM option moving 60% in a day would otherwise fill the whole
        # board and bury the underlyings an admin actually watches.
        if quotes:
            docs = await Instrument.find(
                {"token": {"$in": [q["token"] for q in quotes]}}
            ).to_list()
            by_token = {d.token: d for d in docs}
            named: list[dict[str, Any]] = []
            for row in quotes:
                inst = by_token.get(row["token"])
                segment = str(getattr(inst, "segment", "") or "")
                if not include_options and "OPTION" in segment.upper():
                    continue
                row["symbol"] = inst.symbol if inst else row["token"]
                row["segment"] = segment
                row["exchange"] = (
                    (inst.exchange.value if hasattr(inst.exchange, "value") else str(inst.exchange))
                    if inst
                    else ""
                )
                named.append(row)
            quotes = named

        quotes.sort(key=lambda r: r["change_pct"], reverse=True)
        gainers = [q for q in quotes if q["change_pct"] > 0][:limit]
        losers = [q for q in quotes if q["change_pct"] < 0][-limit:][::-1]
    except Exception:
        logger.exception("top_movers_symbols_failed")

    # ── Clients: realised P&L over the window ───────────────────────────
    since = now_utc() - timedelta(days=days)
    match: dict[str, Any] = {"executed_at": {"$gte": since}, "pnl_inr": {"$ne": None}}
    scope = await scoped_user_ids(admin)
    if scope is not None:
        if not scope:
            return APIResponse(
                data={
                    "symbols": {"gainers": gainers, "losers": losers},
                    "clients": {"gainers": [], "losers": []},
                    "days": days,
                }
            )
        match["user_id"] = {"$in": scope}

    ranked = await Trade.aggregate(
        [
            {"$match": match},
            {
                "$group": {
                    "_id": "$user_id",
                    "pnl": {"$sum": {"$toDouble": "$pnl_inr"}},
                    "trades": {"$sum": 1},
                }
            },
            {"$sort": {"pnl": -1}},
        ]
    ).to_list()

    user_docs = await User.find(
        {"_id": {"$in": [r["_id"] for r in ranked[:limit] + ranked[-limit:]]}}
    ).to_list()
    names = {u.id: u for u in user_docs}

    def _client_row(r: dict[str, Any]) -> dict[str, Any]:
        u = names.get(r["_id"])
        return {
            "user_id": str(r["_id"]),
            "user_code": getattr(u, "user_code", "") or "",
            "name": getattr(u, "full_name", "") or "",
            "pnl": round(r["pnl"], 2),
            "trades": r["trades"],
        }

    client_gainers = [_client_row(r) for r in ranked[:limit] if r["pnl"] > 0]
    client_losers = [_client_row(r) for r in ranked[::-1][:limit] if r["pnl"] < 0]

    return APIResponse(
        data={
            "symbols": {"gainers": gainers, "losers": losers},
            "clients": {"gainers": client_gainers, "losers": client_losers},
            "days": days,
        }
    )
