"""The arithmetic behind the end-of-day carry-forward decision.

Pure functions, no I/O: given a user's open book, their funds and the
overnight requirement, decide HOW MUCH of each position carries overnight and
how much is squared off. The sweep in `position_service` does the talking to
the wallet, the order book and the feed; everything that can be reasoned
about — and got wrong before — lives here where a test can pin it.

The rule the operator asked for: **carry as much as the funds cover.** A book
that is short of the overnight requirement is not flattened; the OLDEST
positions are cut first, the position where the shortfall runs out is cut
PARTIALLY, and everything newer carries in full.

Two subtleties that cost real money before:

* Squaring a position frees its margin LESS the brokerage the square itself
  costs. Planning with the gross margin left every plan short by exactly the
  brokerage, and a carry that the arithmetic said was affordable failed at
  execution.
* The brokerage estimate has to be resolved WITH the option type. Without it
  an option square was priced at the futures rate (Rs 20/lot against the Rs
  100/lot actually charged) and the same shortfall appeared.
"""

from __future__ import annotations

from datetime import time
from decimal import ROUND_FLOOR, Decimal
from typing import Any


def _positive(v: Any) -> Decimal | None:
    """`v` as a Decimal when it is a usable positive number, else None."""
    try:
        d = Decimal(str(v)) if v is not None else None
    except Exception:  # noqa: BLE001 — any unparsable value is simply "no price"
        return None
    return d if d is not None and d > 0 else None


def exit_mark(
    qty: Any,
    quote: dict | None,
    ltp: Any = None,
    last_mark: Any = None,
    avg: Any = None,
) -> Decimal:
    """The price this position would actually leave at.

    A long leaves on the bid and a short on the ask — that is what the user
    gets filled at, and pricing the decision at the mid or the entry flatters
    the plan. Falls back to the live LTP, then the stored mark, then the
    average price, so a dead feed at the close still yields a number.

    A crossed book (bid > ask) is a feed artefact, not a market: both sides
    are dropped rather than trusted.
    """
    q = quote or {}
    bid, ask = _positive(q.get("bid")), _positive(q.get("ask"))
    if bid and ask and bid > ask:
        bid = ask = None
    side = bid if Decimal(str(qty)) > 0 else ask
    for v in (side, ltp, last_mark, avg):
        d = _positive(v)
        if d is not None:
            return d
    return Decimal(0)


def overnight_margin(
    s: dict,
    qty: Any,
    mark: Any,
    lot_size: Any,
    is_usd: bool = False,
    usd_inr: Decimal = Decimal(1),
) -> Decimal:
    """What carrying `qty` overnight has to lock, at `mark`.

    One formula for the rollover, the positions page's "CF required" and NRML
    order validation. They disagreed once: a user topped up by the figure the
    screen showed and was force-closed anyway.

    Fixed mode is already admin-entered in INR, so it never takes the FX step.
    """
    q = abs(Decimal(str(qty)))
    fixed = Decimal(str(s.get("overnight_fixed_margin_per_lot") or 0))
    if s.get("margin_calc_mode") == "fixed" and fixed > 0:
        return round(fixed * q / Decimal(max(1, int(lot_size or 1))), 2)
    pct = Decimal(str(s.get("overnight_margin_percentage") or 100)) / 100
    lev = Decimal(str(s.get("overnight_leverage") or 1))
    lev = lev if lev > 0 else Decimal(1)
    m = q * Decimal(str(mark)) * pct / lev
    if is_usd:
        m *= usd_inr
    return round(m, 2)


def carry_step(min_lot: Any, lot_size: Any) -> Decimal:
    """The smallest quantity a partial carry may keep.

    One unit for anything the exchange trades in whole units; the fractional
    minimum for crypto and forex, where 0.01 of a lot is a real size.
    """
    m = Decimal(str(min_lot or 0)) * Decimal(str(lot_size or 1))
    return m if 0 < m < 1 else Decimal(1)


def floor_to_step(x: Decimal, step: Decimal) -> Decimal:
    """Round DOWN to a whole step — a carry may never round up into money
    the account does not have."""
    return (x / step).to_integral_value(rounding=ROUND_FLOOR) * step


def carry_funds(available: Decimal, locked: Decimal, floating: Decimal) -> Decimal:
    """What an account can put behind the overnight requirement.

    `plan_carry`'s `need` is the FULL overnight margin of the book, not the
    delta over the intraday lock, so the margin those positions already hold
    belongs on this side of the comparison: it is released the moment they
    are squared, or re-locked at the overnight figure.

    Floating P&L counts — equity, not cash. A book sitting on a paper loss
    stops backing a carry, and one sitting on a profit starts; that is the
    stricter direction and the one worth saying out loud.

    The credit limit does NOT count. A carry runs unattended overnight and
    the house is not lending against its own exposure while nobody is
    watching. Credit still backs intraday trading, where somebody is.

    Floored at zero: a floating loss larger than the account would otherwise
    produce a negative capacity, which fails even a book that needs nothing.
    An account that far underwater is the risk enforcer's stop-out to handle.
    """
    funds = available + locked + floating
    return funds if funds > 0 else Decimal(0)


def plan_carry(items: list[tuple], available: Decimal) -> dict:
    """How much of each position carries overnight.

    `items` is `[(key, qty, overnight_margin, square_brokerage, step)]`,
    OLDEST FIRST — portfolio FIFO, so the position held longest is cut before
    one opened this afternoon. Returns `{key: qty_to_carry}`.

    Everything fits -> everything carries. Otherwise positions are cut from
    the oldest end until the shortfall is covered: whole while the margin
    they free is still less than the gap, then PARTIALLY on the one where the
    gap runs out. Every newer position carries untouched.
    """
    plan = {key: qty for key, qty, *_ in items}
    need = sum((it[2] for it in items), Decimal(0))
    if need <= available:
        return plan  # everything fits -> everything carries
    released = Decimal(0)
    for key, qty, margin, brokerage, step in items:
        gap = (need - available) - released
        if gap <= 0:
            break  # newer positions carry in full
        net = max(margin - brokerage, Decimal(0))  # squaring frees margin LESS its brokerage
        if margin <= 0 or net <= gap:
            plan[key] = Decimal(0)  # square this one whole
            released += net
            continue
        keep = floor_to_step(qty * (net - gap) / net, step)  # boundary position: partial
        plan[key] = keep
        released += (qty - keep) / qty * net
    return plan


def affordable_carry(
    qty: Decimal, cash: Decimal, locked: Decimal, full_margin: Decimal, step: Decimal
) -> Decimal:
    """The executor's last resort when a planned flip cannot be funded.

    Keeps what cash plus the margin already locked covers, one step short as
    headroom — the plan was built on a mark that has since moved, and a carry
    that lands exactly on the limit fails again on the next recalculation.
    """
    if full_margin <= 0:
        return qty
    keep = floor_to_step(qty * (cash + locked) / full_margin, step) - step
    return max(min(keep, qty - step), Decimal(0))


def rollover_fire_time(close: time, delay_min: int) -> time:
    """Close + delay, as a wall-clock time.

    Via `divmod`, because adding minutes naively produces "15:66", which no
    clock ever reads — the group's rollover then silently skipped every day.
    Clamped to 23:59 so a late MCX close cannot roll past midnight and land
    on tomorrow's date key.
    """
    h, m = divmod(close.hour * 60 + close.minute + delay_min, 60)
    return time(23, 59) if h > 23 else time(h, m)
