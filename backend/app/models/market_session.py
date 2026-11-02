"""Operator overrides for a segment group's trading session.

The session times live in `app.utils.time_utils` as code defaults, and this
collection only OVERRIDES them. That direction is deliberate: a worker that
cannot reach Mongo, or a fresh database with no rows, behaves exactly as the
platform did before this collection existed. The alternative — the schedule
living only here — would mean a cold worker resolves no close time at all,
`is_after_close` returns False for everything, and the platform decides the
market never shuts: parked orders fire and the risk enforcer books stop-outs
against an overnight tick, forever.

One row per GROUP, not per segment. Segments inside a group share an exchange
session (NFO trades on NSE's clock), and `time_utils` already groups them that
way; a per-segment row would let NFO and NSE_EQ drift apart, which no exchange
does.

Forex and crypto have no row. They are 24×5 / 24×7 and `time_utils` returns
None for them, which is what marks them rollover-exempt — giving them a
session here would start squaring them off at a close they do not have.
"""

from __future__ import annotations

from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.utils.time_utils import now_utc

# The groups that HAVE a daily session. Kept in step with the membership sets
# in `time_utils` by `backend/tests/test_market_session_override.py`.
SESSION_GROUPS: tuple[str, ...] = ("NSE_BSE", "MCX")


class MarketSession(Document):
    group: str  # one of SESSION_GROUPS

    # "HH:MM" IST, or None to keep the code default for that field. Stored as
    # strings so a half-written row can be rejected at parse time by the
    # resolver and fall back, rather than becoming a `time` nobody intended.
    open_time: str | None = None
    # The order validator's cutoff for accepting NEW orders.
    entry_close: str | None = None
    # When `is_after_close` starts treating the session as over — this is what
    # silences the pending-order poller and the risk enforcer and fires the EOD
    # rollover. Deliberately separable from `entry_close`: NSE/BSE runs the
    # gate 30 min past the 15:30 bell so late prints settle first.
    gate_close: str | None = None

    # MCX only. True (the default) keeps the close derived from US daylight
    # saving, which is what the exchange's circulars track; the override fields
    # above are then ignored for the closes. Turning it off freezes the twice-
    # yearly flip, so the admin UI says so where it is set.
    auto_dst: bool = True

    updated_at: datetime = Field(default_factory=now_utc)
    updated_by: PydanticObjectId | None = None

    class Settings:
        name = "market_sessions"
        indexes = [IndexModel([("group", ASCENDING)], unique=True)]
