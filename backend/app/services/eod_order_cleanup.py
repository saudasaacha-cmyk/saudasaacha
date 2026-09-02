"""End-of-day auto-cancel for parked DAY orders (NSE + MCX).

WHY THIS EXISTS
---------------
A LIMIT / SL-M order the user parks sits as ``OPEN`` in the ``orders``
collection and the ``pending_order_poller`` only ever *fires* it when its
trigger is hit — nothing ever *expires* it. So an unfilled NSE/MCX pending
order (or an SL / TP leg) survived past the session and carried into the
NEXT trading day, firing on the next day's prices. That's the operator-
reported "pending order dusre din carry forward ho jaata hai" bug.

Real brokers treat a ``DAY`` order as valid for ONE session: if it hasn't
filled by end of day it is cancelled. This loop restores that: a single
sweep just after **00:00 IST** expires every still-parked ``LIMIT`` /
``SL-M`` order on Indian exchange segments (NSE / BSE / NFO / BFO / MCX),
releases the margin it had blocked, and marks it ``EXPIRED`` so it can't
fire the next day.

SCOPE (operator decision, Jul 2026)
------------------------------------
  • Indian equity + F&O (NSE / BSE / NFO / BFO) and MCX ONLY.
  • Forex (CDS, 24×5) and crypto (24×7) are EXEMPT — those markets trade
    overnight, so a midnight cancel would kill live orders.

AMO HANDLING
------------
An AMO (After-Market Order) is placed in the evening FOR THE NEXT session,
so it must survive the midnight that immediately follows its placement.
It is given exactly one session: the sweep only expires an AMO once it is
older than the START of the previous IST day (i.e. it has already lived
through its intended session and still didn't fill). A normal DAY order is
expired at the very next midnight after the calendar day it was placed on.

SAFETY / PLACEMENT
------------------
Mongo-only (no in-process price state), so it is safe on ANY worker and
runs under its OWN ``leader:eod_order_cleanup`` lock (NOT the ``leader:feed``
gate). The sweep is idempotent — a second run finds no OPEN/PARTIAL rows to
expire — so an extra fire on a mid-day restart is harmless.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta, timezone

from app.models._base import OrderType
from app.models.order import Order, OrderStatus
from app.services import wallet_service
from app.utils.decimal_utils import to_decimal
from app.utils.time_utils import now_ist, now_utc, start_of_day_ist, to_utc

logger = logging.getLogger(__name__)

_UTC = timezone.utc

# Module-level kill switch + per-day run guard (same pattern as the
# intraday→carry rollover loop). `_last_run_day` is the IST YYYYMMDD the
# sweep last completed, so we fire exactly once per calendar day.
_stop = False
_last_run_day: str | None = None


def stop_eod_order_cleanup() -> None:
    global _stop
    _stop = True


def _is_nse_mcx_segment(segment: str | None) -> bool:
    """True for Indian equity / F&O / MCX segments only.

    Prefix match (not the fixed segment sets) so any Zerodha-CSV variant
    — NSE_FUT / NFO_OPTION / BFO_OPT / MCX_FUT … — is caught. Deliberately
    EXCLUDES CDS (forex, 24×5) and CRYPTO (24×7), which trade overnight and
    must not be swept at midnight.
    """
    if not segment:
        return False
    return segment.upper().startswith(("NSE", "BSE", "NFO", "BFO", "MCX"))


async def expire_stale_day_orders() -> dict[str, int]:
    """One EOD sweep. Expires still-parked NSE/MCX LIMIT/SL-M orders whose
    session is over, releasing their blocked margin. Never raises — one bad
    order must not stop the rest. Returns ``{scanned, expired}``.
    """
    global _last_run_day  # noqa: F824 — documented; not mutated here

    try:
        rows = await Order.find(
            {
                "status": {"$in": [OrderStatus.OPEN.value, OrderStatus.PARTIAL.value]},
                "order_type": {"$in": [OrderType.LIMIT.value, OrderType.SL_M.value]},
            }
        ).to_list()
    except Exception:
        logger.exception("eod_order_scan_failed")
        return {"scanned": 0, "expired": 0}

    if not rows:
        return {"scanned": 0, "expired": 0}

    now = now_ist()
    today_start_utc = to_utc(start_of_day_ist(now.date()))
    # AMO gets one full session — only expired once older than the START of
    # the PREVIOUS IST day (it already had its session and didn't fill).
    amo_cutoff_utc = to_utc(start_of_day_ist(now.date() - timedelta(days=1)))

    expired = 0
    affected_users: set[str] = set()

    for o in rows:
        try:
            seg = getattr(o.instrument, "segment", None)
            if not _is_nse_mcx_segment(str(seg) if seg else None):
                continue

            created = o.created_at
            if created is not None and created.tzinfo is None:
                created = created.replace(tzinfo=_UTC)
            cutoff = amo_cutoff_utc if o.is_amo else today_start_utc
            if created is None or created >= cutoff:
                continue

            o.status = OrderStatus.EXPIRED
            o.cancelled_at = now_utc()
            o.rejection_reason = "DAY order expired at end of day (auto-cancelled)"
            o.rejection_code = "DAY_ORDER_EOD_EXPIRED"
            o.pending_quantity = 0
            await o.save()

            margin = to_decimal(o.margin_blocked)
            if margin > 0:
                try:
                    await wallet_service.release_margin(o.user_id, margin)
                except Exception:
                    logger.exception(
                        "eod_order_margin_release_failed",
                        extra={"order_id": str(o.id), "user_id": str(o.user_id)},
                    )

            expired += 1
            affected_users.add(str(o.user_id))
            logger.info(
                "eod_order_expired",
                extra={
                    "order_id": str(o.id),
                    "user_id": str(o.user_id),
                    "symbol": o.instrument.symbol,
                    "segment": str(seg),
                    "order_type": o.order_type.value if hasattr(o.order_type, "value") else str(o.order_type),
                    "is_amo": bool(o.is_amo),
                },
            )
        except Exception:
            logger.exception(
                "eod_order_expire_failed",
                extra={"order_id": str(getattr(o, "id", None))},
            )

    # Refresh the admin dashboard + affected users' Orders/wallet views so
    # the cancellations show without an F5. Fire-and-forget — pure WS pings,
    # they must never fail the sweep.
    if affected_users:
        try:
            from app.services.admin_events import publish_admin_event
            from app.utils.background import fire_and_forget

            for uid in affected_users:
                fire_and_forget(
                    publish_admin_event(
                        "order_update",
                        {"event": "eod_expired", "user_id": uid},
                    ),
                    label="eod_order_update",
                )
                fire_and_forget(
                    publish_admin_event("wallet_update", {"user_id": uid}),
                    label="eod_wallet_update",
                )
        except Exception:
            logger.exception("eod_order_admin_event_failed")

    return {"scanned": len(rows), "expired": expired}


async def eod_order_cleanup_loop(interval_sec: float = 60.0) -> None:
    """Wake every minute; run the EOD sweep exactly ONCE per IST calendar
    day, the first tick after midnight (00:00 IST). Also runs once on boot
    so anything left parked from a previous day is cleaned at startup.
    """
    global _stop, _last_run_day
    _stop = False
    logger.info("eod_order_cleanup_started", extra={"interval_sec": interval_sec})
    while not _stop:
        try:
            day_key = now_ist().strftime("%Y%m%d")
            if _last_run_day != day_key:
                summary = await expire_stale_day_orders()
                _last_run_day = day_key
                logger.info("eod_order_cleanup_swept", extra={"day": day_key, **summary})
        except Exception:
            logger.exception("eod_order_cleanup_loop_failed")
        try:
            await asyncio.sleep(interval_sec)
        except asyncio.CancelledError:
            return
