"""The EOD sweep must run once per DAY, not once per restart.

`clear_carry_brackets` wipes SL/TP off every open position carrying
overnight in a segment whose cutoff has passed. That is a deliberate
operator decision — brackets are day-scoped like the parked orders — and
it is safe exactly once.

The guard that enforced "once" was a module-level dict, so a restart
handed the sweep a blank slate and it ran again. Harmless for the order
cancellations, which are idempotent; not harmless here, because a user
who re-set their stop after the first sweep lost it again on the next
deploy.

Seen in production on 2026-10-22, with the backend restarting between
each pair: position 4acec4 cleared at 08:43 and again at 10:29, position
901a4f at 08:43 and again at 11:19. Same positions, same day. That is
what the client meant by "SL/TP set kar rahe hain, hat ja raha hai", and
why it never reproduced in a test that did not span a restart.

    pytest -q backend/tests/test_eod_run_guard.py
"""

from __future__ import annotations

import ast
import inspect
import textwrap

from app.services import eod_order_cleanup as eod


def test_the_run_mark_survives_a_restart():
    """In Redis, not in a dict. A process-local mark is not a day mark."""
    for name in ("_last_swept", "_mark_swept", "_mark_key"):
        assert hasattr(eod, name), name
    src = inspect.getsource(eod._mark_swept)
    assert "get_redis()" in src
    assert "ex=" in src, "the mark must expire on its own rather than linger forever"


def test_the_sweep_asks_the_durable_mark_not_the_dict():
    """The dict is still there as a per-process fast path, so the 60-second
    'nothing due' poll costs no round trip — but the decision to RUN has to
    come from the durable one."""
    src = textwrap.dedent(inspect.getsource(eod.expire_stale_day_orders))
    tree = ast.parse(src)
    calls = {
        ast.unparse(n.func)
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
    }
    assert "_last_swept" in calls, "the due-check still reads process state"
    assert "_last_run_day.get" not in src, "the dict is being consulted directly again"


def test_the_mark_is_written_only_after_the_sweep_finishes():
    """Marking first would lose a day's sweep to a crash halfway through;
    marking last means a crash re-runs it, which is the safe direction for
    the order half and the only direction that is safe at all for the
    bracket half."""
    src = textwrap.dedent(inspect.getsource(eod.expire_stale_day_orders))
    assert src.index("clear_carry_brackets(") < src.index("_mark_swept(")


def test_clearing_brackets_is_still_gated_on_the_segment():
    """It leaves a carried position unprotected overnight, which is why the
    setting is per segment rather than global. Pinned so a future tidy-up
    does not quietly make it platform-wide."""
    src = inspect.getsource(eod.clear_carry_brackets)
    assert "seg_names" in src
    assert "admin_row_for_segment" in src


def test_a_redis_outage_does_not_block_the_sweep():
    """Both helpers swallow and log. A cache blip must not stop end-of-day
    from happening at all — re-running is recoverable, never running is
    not."""
    for fn in (eod._last_swept, eod._mark_swept):
        assert "except Exception" in inspect.getsource(fn), fn.__name__
