"""Keeps each worker's session-override snapshot in step with the collection.

`time_utils` resolves every session gate synchronously — `is_after_close` is
called by the risk enforcer on every one-second tick — so it cannot read the
database itself. This loop pushes the rows in instead, on EVERY worker rather
than only the leader, because every worker validates orders and answers the
admin panel.

Two rules the loop must never break:

  • A failed read leaves the previous snapshot in place. Clearing it would
    revert the whole platform to the code defaults mid-session on a transient
    Mongo blip, which is a silent change to live risk gates.
  • An unknown group is dropped rather than passed through. `time_utils` only
    understands "NSE_BSE" and "MCX"; a stray row cannot be allowed to sit in
    the snapshot looking authoritative.
"""

from __future__ import annotations

import asyncio
import logging

from app.models.market_session import SESSION_GROUPS, MarketSession
from app.utils.time_utils import set_session_overrides

logger = logging.getLogger(__name__)

# 30 s. Nobody changes a market session and needs it live in five seconds, and
# the admin status screen polls at 10 s so the operator watches it land.
_INTERVAL_SEC = 30.0
_stop = False


async def refresh_once() -> dict[str, dict]:
    """Pull the rows and install them. Returns what was installed, for the
    caller that wants to confirm (the admin PUT, and the tests)."""
    rows = await MarketSession.find_all().to_list()
    snapshot = {
        r.group: {
            "open_time": r.open_time,
            "entry_close": r.entry_close,
            "gate_close": r.gate_close,
            "auto_dst": r.auto_dst,
        }
        for r in rows
        if r.group in SESSION_GROUPS
    }
    set_session_overrides(snapshot)
    return snapshot


async def market_session_refresh_loop(interval_sec: float = _INTERVAL_SEC) -> None:
    global _stop  # noqa: PLW0603 - module-level stop flag, as the other loops here do
    _stop = False
    logger.info("market_session_refresh_loop_started")
    try:
        while not _stop:
            try:
                await refresh_once()
            except Exception:  # noqa: BLE001
                # Deliberately does NOT clear the snapshot — see the module
                # docstring. Last known good keeps serving.
                logger.warning("market_session_refresh_failed", exc_info=True)
            await asyncio.sleep(interval_sec)
    finally:
        logger.info("market_session_refresh_loop_stopped")


def stop_market_session_refresh() -> None:
    global _stop  # noqa: PLW0603
    _stop = True
