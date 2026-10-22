"""Replacing a per-fill SL/TP must never leave the position bare.

Setting SL/TP on an Active-trade row does not write a number on the
position — it parks REAL exit orders (`LIMIT` for the target, `SL_M` for
the stop) that close only that fill, and then clears the whole-position
bracket so the risk enforcer cannot double-fire.

That makes the edit a replace, and the order of the replace is the whole
bug. It used to cancel the live exits and then place the new ones.
`order_service.place_order` persists a REJECTED row and RE-RAISES, and
one of the things it rejects on is a stale price —

    GOLD26DECFUT: price has not moved for 27s (limit 5s)

— which on a thin MCX future is an ordinary afternoon. So editing a stop
on a quiet contract cancelled the live exit, failed to park the
replacement, and left the position with no protection at all. The
endpoint returned an error, but the stop was already gone. Production
carried 67 rejected exits with that reason across NATURALGAS, GOLD,
SILVERM, ZINC and CRUDEOIL, against 43 cancels, and zero that were ever
live.

Placing first means a failed replacement leaves the user exactly as they
were.

    pytest -q backend/tests/test_sltp_replace_order.py
"""

from __future__ import annotations

import ast
import inspect
import textwrap

from app.api.v1.user import positions as pos_api

SRC = textwrap.dedent(inspect.getsource(pos_api._ensure_fill_sl_tp))


def _lineno_of_first(pred) -> int:
    tree = ast.parse(SRC)
    for node in ast.walk(tree):
        if pred(node):
            return node.lineno
    raise AssertionError("not found")


def test_the_replacement_is_placed_before_the_old_one_is_cancelled():
    """The single assertion this whole file exists for."""
    place = _lineno_of_first(
        lambda n: isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "place_order"
    )
    cancel = _lineno_of_first(
        lambda n: isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "cancel"
    )
    assert place < cancel, (
        "cancel runs before place again — a rejected replacement now "
        "leaves the position with no SL/TP at all"
    )


def test_the_position_bracket_is_cleared_last():
    """Clearing it is what hands ownership to the exit orders, so it must
    not happen until those orders exist. `place_order` re-raises on
    rejection, so anything after it is only reached on success."""
    assert "p.stop_loss = None" in SRC
    place = SRC.index("place_order")
    clear = SRC.index("p.stop_loss = None")
    assert place < clear


def test_a_failed_cancel_is_logged_not_swallowed_silently():
    """It was a bare `except: pass`. After the reorder a stuck old leg is a
    duplicate rather than a gap — the OCO group clears it — but silence is
    how the original ordering survived unnoticed for so long."""
    assert "except Exception" in SRC
    assert "logger" in SRC, "the failure path writes nothing at all"


def test_the_legs_share_one_oco_group():
    """Placing before cancelling means the new and old legs briefly
    coexist. That is only safe because a fire cancels its siblings."""
    assert "oco_group_id" in SRC


def test_both_legs_still_close_only_their_own_fill():
    """`cost_basis_override` + `force_quantity` are what make this per-FILL
    rather than per-position. Lose them and an SL set on one lot closes
    every lot of the symbol — the bug this mode was built to fix."""
    for pin in ("cost_basis_override", "force_quantity", "is_squareoff"):
        assert pin in SRC, pin
