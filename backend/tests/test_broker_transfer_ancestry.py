"""Transferring a sub-broker must take its clients OUT of the old tenant.

`reassign_user` cleared the moved broker's own chain and re-stamped its
subtree's `assigned_admin_id` — and stopped. The descendants kept the ids of
the brokers that used to sit ABOVE it, and those brokers still belong to the
old admin, so `_admin_pool_clause` arm 3 and the old parent broker's own
`{"broker_ancestry": parent.id}` clause both kept matching them. Move B2 from
admin A to admin X and client C was listed under A *and* X at once — lists,
dashboards, P&L, money transactions, exports — with nothing to expire it.

Pure: the update document is built by a function, and the migration's walk is
a function, so the leak and its repair are both provable without a database.
`mini_update` below is a 10-line stand-in for the two Mongo operators used.

    pytest -q backend/tests/test_broker_transfer_ancestry.py
"""

from __future__ import annotations

import ast
import inspect

from app.services.admin_management_service import _subtree_transfer_update, reassign_user
from scripts.backfill_broker_ancestry import correct_ancestry

A, X = "adminA", "adminX"
B1, B2, B3 = "B1", "B2", "B3"  # B1 owns B2 owns B3; B2 is the one that moves


def mini_update(doc: dict, update: dict) -> dict:
    """Just enough of `$set` / `$pull: {$in: [...]}` to apply a real update
    document to a real-shaped row. Mongo applies every operator in one
    document atomically; so does this."""
    out = dict(doc)
    for field, value in update.get("$set", {}).items():
        out[field] = value
    for field, cond in update.get("$pull", {}).items():
        drop = set(cond["$in"])
        out[field] = [x for x in out[field] if x not in drop]
    return out


def visible_to_admin(doc: dict, admin_id: str, admin_brokers: list[str]) -> bool:
    """`_admin_pool_clause` in three lines: direct ownership, direct broker,
    or anywhere in one of that admin's brokers' subtrees."""
    return (
        doc["assigned_admin_id"] == admin_id
        or doc["assigned_broker_id"] in admin_brokers
        or any(b in doc["broker_ancestry"] for b in admin_brokers)
    )


def test_the_moved_subtree_leaves_the_old_admins_pool():
    """The bug, end to end. C sits under B2 which sat under B1 (admin A's
    broker). After the move only admin X may see C."""
    c = {"assigned_admin_id": A, "assigned_broker_id": B2, "broker_ancestry": [B1, B2]}

    assert visible_to_admin(c, A, [B1, B2])  # before: A's, correctly

    c = mini_update(c, _subtree_transfer_update(X, [B1]))

    assert not visible_to_admin(c, A, [B1])  # B2 is X's broker now, A keeps only B1
    assert visible_to_admin(c, X, [B2])


def test_the_old_parent_broker_also_stops_seeing_them():
    """B1's own scope clause is `{"broker_ancestry": B1.id}` — a separate
    login from admin A's, and it was leaking the same rows."""
    c = {"assigned_admin_id": A, "assigned_broker_id": B2, "broker_ancestry": [B1, B2]}

    assert B1 in c["broker_ancestry"]

    c = mini_update(c, _subtree_transfer_update(X, [B1]))

    assert B1 not in c["broker_ancestry"]


def test_the_moved_broker_stays_their_ancestor():
    """The `$pull` must take the prefix and nothing else: strip B2 as well
    and the subtree falls out of BOTH tenants — invisible, not just
    misfiled."""
    c = {"assigned_admin_id": A, "assigned_broker_id": B2, "broker_ancestry": [B1, B2]}

    c = mini_update(c, _subtree_transfer_update(X, [B1]))

    assert c["broker_ancestry"] == [B2]
    assert c["assigned_broker_id"] == B2  # the client's own broker didn't change


def test_the_whole_depth_of_the_subtree_is_repaired_by_one_update():
    """A grandchild under B3 under B2: the same `$in` list fixes every depth,
    which is why one `update_many` is enough."""
    update = _subtree_transfer_update(X, [B1])
    deep = {"assigned_admin_id": A, "assigned_broker_id": B3, "broker_ancestry": [B1, B2, B3]}

    assert mini_update(deep, update)["broker_ancestry"] == [B2, B3]


def test_moving_a_top_level_broker_still_writes_only_the_owner():
    """A broker with no parent has nothing to pull. The update must stay
    exactly what it was before the fix — no empty `$pull`, which Mongo takes
    but which would rewrite every descendant's array for nothing."""
    assert _subtree_transfer_update(X, []) == {"$set": {"assigned_admin_id": X}}


def test_set_and_pull_never_touch_the_same_field():
    """They ride in ONE update document, so a shared path would be a
    hard Mongo conflict error — and the atomicity is the point: no descendant
    may ever hold the new owner together with the old ancestry."""
    update = _subtree_transfer_update(X, [B1])

    assert set(update) == {"$set", "$pull"}
    assert set(update["$set"]) & set(update["$pull"]) == set()


def test_the_ancestry_is_read_before_it_is_cleared():
    """`target.broker_ancestry = []` happens on the same row; read it after
    and the `$pull` list is empty and the leak is back, silently."""
    src = inspect.getsource(reassign_user)
    read_at = src.index("old_ancestry = ")
    cleared_at = src.index("target.broker_ancestry = []")

    assert read_at < cleared_at


def test_a_failed_subtree_migration_is_not_swallowed():
    """Half a migrated tree is a split tenant. The old handler was a bare
    `pass`, so it left no trace anywhere to find it by."""
    tree = ast.parse(inspect.getsource(reassign_user).lstrip())
    tries = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Try) and "update_many" in ast.unparse(n.body)
    ]

    assert len(tries) == 1
    for handler in tries[0].handlers:
        assert not all(isinstance(s, ast.Pass) for s in handler.body)
        assert "logger" in ast.unparse(handler.body)


# ── the migration's walk (scripts/backfill_broker_ancestry.py) ───────


def test_the_migration_recomputes_root_first_excluding_self():
    """The documented shape of `User.broker_ancestry`. Getting the order
    backwards would break `broker_ancestry[-1]` — which is how the broker
    settlement and money-transaction code find a client's OWN broker."""
    parent_of = {B1: None, B2: B1, B3: B2, "C": B3}

    assert correct_ancestry("C", parent_of) == ([B1, B2, B3], None)
    assert correct_ancestry(B1, parent_of) == ([], None)


def test_the_migration_ignores_the_damaged_value_entirely():
    """It walks `assigned_broker_id`, so a row whose stored array still has
    the stale prefix is recomputed correctly, not patched."""
    parent_of = {B2: None, "C": B2}  # post-transfer: B2 is top-level again

    assert correct_ancestry("C", parent_of) == ([B2], None)


def test_a_cycle_is_reported_instead_of_looping_forever():
    """Two brokers pointing at each other is corrupt data, not a tree. No
    correct ancestry exists, so the row is flagged and left alone."""
    assert correct_ancestry("C", {B1: B2, B2: B1, "C": B1}) == ([], "cycle")
    assert correct_ancestry(B1, {B1: B1}) == ([], "cycle")


def test_a_deleted_parent_truncates_the_chain_and_says_so():
    """Mid-chain broker deleted by hand: keep the part that is still known
    rather than writing a chain through a user that doesn't exist."""
    ancestry, problem = correct_ancestry("C", {B3: "GONE", "C": B3})

    assert ancestry == [B3]
    assert problem == "dangling:GONE"
