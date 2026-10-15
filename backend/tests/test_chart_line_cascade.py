"""Whose chart lines a user actually sees.

Reported by the operator: "super admin se change kar raha hu tab vo sirf
super admin ke user ke liye ho raha hai, admin broker subbroker ke user ke
liye nahi ho raha" — and the other half: an admin's change has to reach
every broker and sub-broker underneath them.

The cause was a flag. `_owner_cascade` took `include_platform`, which the
VISIBILITY path passed as True and the LINES path as False, so for lines a
user with an `assigned_admin_id` stopped one step short of the platform
row — and the super admin's rows ARE the platform row (owner ids both
None, see `owner_filter_for_admin`). Result: a platform-wide change
reached only the super admin's own direct clients.

These assert the ORDER of the cascade, which is the whole behaviour:
closest owner wins, and the list must end at the platform so that a tier
which has set nothing inherits instead of showing an empty chart. Pure
function, no Mongo and no Redis.

    pytest -q backend/tests/test_chart_line_cascade.py
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from types import SimpleNamespace

from beanie import PydanticObjectId

import app.services.chart_level_service as svc
from app.models.user import UserRole
from app.services.chart_level_service import _owner_cascade, owner_filter_for_admin

SUPER = {"owner_admin_id": None, "owner_broker_id": None}

ADMIN_A = PydanticObjectId()
BROKER_B = PydanticObjectId()
SUB_BROKER_SB = PydanticObjectId()


def _user(*, admin=None, broker=None, ancestry=()):
    return SimpleNamespace(
        assigned_admin_id=admin,
        assigned_broker_id=broker,
        broker_ancestry=list(ancestry),
    )


def test_a_super_admin_change_reaches_an_admins_user():
    """The reported bug, as the operator saw it. This user belongs to admin
    A; A has set nothing. The platform row must be in their cascade, or the
    super admin's upload is invisible to everyone but their own clients."""
    chain = _owner_cascade(_user(admin=ADMIN_A))
    assert SUPER in chain, chain
    # ...and only AFTER the admin, so A still overrides when A does set rows.
    assert chain.index({"owner_admin_id": ADMIN_A, "owner_broker_id": None}) < chain.index(SUPER)


def test_a_super_admin_change_reaches_a_sub_brokers_user():
    """Deepest case: client → sub-broker SB → broker B → admin A. Every tier
    above is consulted, ending at the platform."""
    chain = _owner_cascade(
        _user(admin=ADMIN_A, broker=SUB_BROKER_SB, ancestry=(BROKER_B, SUB_BROKER_SB))
    )
    assert chain == [
        {"owner_admin_id": None, "owner_broker_id": SUB_BROKER_SB},
        {"owner_admin_id": None, "owner_broker_id": BROKER_B},
        {"owner_admin_id": ADMIN_A, "owner_broker_id": None},
        SUPER,
    ], chain


def test_an_admins_change_reaches_every_broker_beneath_them():
    """The second half of the request: set it on the admin, and the brokers
    and sub-brokers under that admin inherit it — provided they have not set
    their own. Ordering is what encodes that."""
    chain = _owner_cascade(_user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,)))
    admin_at = chain.index({"owner_admin_id": ADMIN_A, "owner_broker_id": None})
    broker_at = chain.index({"owner_admin_id": None, "owner_broker_id": BROKER_B})
    # The broker is consulted first — their own rows override the admin's —
    # but the admin IS consulted, which is what makes inheritance work.
    assert broker_at < admin_at < chain.index(SUPER)


def test_the_nearest_owner_still_wins():
    """Inheriting upward must not become 'the platform overrides everyone'.
    The platform is LAST in every chain, so any tier that has set rows beats
    it."""
    for chain in (
        _owner_cascade(_user(admin=ADMIN_A)),
        _owner_cascade(_user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,))),
        _owner_cascade(_user(broker=BROKER_B, ancestry=(BROKER_B,))),
    ):
        assert chain[-1] == SUPER, chain
        assert len(chain) == len(set(map(str, chain))), f"duplicate tier: {chain}"


def test_the_super_admins_own_users_are_unchanged():
    """A user with no admin and no broker had the platform row already. The
    fix must not have moved their behaviour at all."""
    assert _owner_cascade(_user()) == [SUPER]


def test_the_super_admin_writes_to_the_row_the_cascade_ends_on():
    """The two halves have to agree: if `owner_filter_for_admin` ever stopped
    writing super-admin rows to (None, None), the cascade would end on a row
    nobody writes and the bug would be back with no test failing."""
    su = SimpleNamespace(role=UserRole.SUPER_ADMIN, id=PydanticObjectId())
    assert owner_filter_for_admin(su) == SUPER


def test_there_is_only_one_cascade():
    """The flag that caused this is gone, not flipped. Two cascades that are
    meant to agree but are selected by a boolean is exactly how lines and
    visibility drifted apart in the first place."""
    # Checked over the AST, not the text — the docstring above names the
    # flag in order to explain why it is gone, and a grep cannot tell the
    # explanation from the thing it explains.
    sig = inspect.signature(_owner_cascade)
    assert list(sig.parameters) == ["user"], sig

    tree = ast.parse(pathlib.Path(svc.__file__).read_text(encoding="utf-8"))
    passed = [
        kw.arg
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "include_platform"
    ]
    assert not passed, "a caller is still selecting between two cascades"
