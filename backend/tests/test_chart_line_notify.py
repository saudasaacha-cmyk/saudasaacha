"""Who hears that the chart lines changed.

The operator's rule: "jisme change hua uske niche jitne aate hain usko
notification chala jayega" — super admin changes it and every user hears;
an admin changes it and that admin's users plus every broker and
sub-broker under them hear; a broker changes it and that broker's subtree
hears.

Two mistakes in the first version are pinned here, because both failed
invisibly — nobody files a ticket about a notification they never got:

  * the shadow check asked a per-OWNER question of per-TOKEN data. Chart
    lines resolve per (owner, token), so an admin holding ONE row for GOLD
    suppressed EVERY super-admin announcement to that admin's whole pool,
    for all the other instruments too. The "precision" filter turned "sab
    user ko jayega" into almost nobody. See
    `test_one_unrelated_row_does_not_mute_a_whole_pool`.

  * it published to `user:{id}:notification`, described in its own comment
    as "bell + live socket, deliberately not a push". That envelope is
    handled at `UserWsBridge.tsx:241` by raising an OS tray notification
    through the service worker, playing a sound, and reading the message
    aloud over text-to-speech. One admin typing one price would have made
    every connected terminal talk.

`_change_reaches` is the whole rule and it is pure, so this needs no Mongo
and no Redis.

    pytest -q backend/tests/test_chart_line_notify.py
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from types import SimpleNamespace

from beanie import PydanticObjectId

from app.api.v1.admin import chart_levels as api
from app.services.chart_level_service import (
    _CHART_ROLES,
    _change_reaches,
    _owner_cascade,
    _owner_key,
    import_workbook,
    notify_levels_changed,
    save_levels,
)

ADMIN_A = PydanticObjectId()
ADMIN_OTHER = PydanticObjectId()
BROKER_B = PydanticObjectId()
SUB_BROKER = PydanticObjectId()

SUPER_KEY = (None, None)
ADMIN_A_KEY = (str(ADMIN_A), None)
BROKER_B_KEY = (None, str(BROKER_B))

GOLD, NIFTY = "GOLD", "NIFTY"


def _user(*, admin=None, broker=None, ancestry=()):
    return SimpleNamespace(
        assigned_admin_id=admin,
        assigned_broker_id=broker,
        broker_ancestry=list(ancestry),
    )


def _reaches(user, own_key, tokens=(GOLD,), *, holders=(), vis=None):
    return _change_reaches(
        _owner_cascade(user), own_key, set(tokens), set(holders), vis or {}
    )


# ── the rule the operator asked for ──────────────────────────────────
def test_a_super_admin_change_reaches_everybody():
    for user in (
        _user(),
        _user(admin=ADMIN_A),
        _user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,)),
        _user(admin=ADMIN_A, broker=SUB_BROKER, ancestry=(BROKER_B, SUB_BROKER)),
    ):
        assert _reaches(user, SUPER_KEY) is True


def test_an_admin_change_reaches_their_brokers_and_sub_brokers():
    for user in (
        _user(admin=ADMIN_A),
        _user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,)),
        _user(admin=ADMIN_A, broker=SUB_BROKER, ancestry=(BROKER_B, SUB_BROKER)),
    ):
        assert _reaches(user, ADMIN_A_KEY) is True


def test_an_admin_change_does_not_cross_into_another_admins_users():
    assert _reaches(_user(admin=ADMIN_OTHER), ADMIN_A_KEY) is False
    assert _reaches(_user(), ADMIN_A_KEY) is False, "the super admin's own client"


def test_a_broker_change_reaches_only_that_brokers_subtree():
    assert _reaches(_user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,)), BROKER_B_KEY)
    assert _reaches(
        _user(admin=ADMIN_A, broker=SUB_BROKER, ancestry=(BROKER_B, SUB_BROKER)), BROKER_B_KEY
    )
    assert _reaches(_user(admin=ADMIN_A), BROKER_B_KEY) is False


# ── per-instrument, which is the part that was wrong ─────────────────
def test_an_override_on_the_same_instrument_does_mute_it():
    """Admin A holds GOLD. The super admin edits GOLD. This user keeps
    drawing A's line, so telling them it changed would be false."""
    user = _user(admin=ADMIN_A)
    assert _reaches(user, SUPER_KEY, (GOLD,), holders=[(ADMIN_A_KEY, GOLD)]) is False
    assert _reaches(user, ADMIN_A_KEY, (GOLD,), holders=[(ADMIN_A_KEY, GOLD)]) is True


def test_one_unrelated_row_does_not_mute_a_whole_pool():
    """THE regression. Admin A holds a row for GOLD and nothing else. The
    super admin edits NIFTY, which A does not override — this user's NIFTY
    chart demonstrably changes, so they must be told.

    The first version grouped holders by owner with no token, so A's single
    GOLD row suppressed every super-admin announcement to A's entire pool."""
    user = _user(admin=ADMIN_A)
    assert _reaches(user, SUPER_KEY, (NIFTY,), holders=[(ADMIN_A_KEY, GOLD)]) is True


def test_a_mixed_sheet_reaches_anyone_one_instrument_got_through():
    """An upload touches many instruments. If even one is unshadowed for
    this user, their chart moved and they hear about it once."""
    user = _user(admin=ADMIN_A)
    assert _reaches(user, SUPER_KEY, (GOLD, NIFTY), holders=[(ADMIN_A_KEY, GOLD)]) is True
    assert (
        _reaches(
            user,
            SUPER_KEY,
            (GOLD, NIFTY),
            holders=[(ADMIN_A_KEY, GOLD), (ADMIN_A_KEY, NIFTY)],
        )
        is False
    )


def test_a_brokers_own_row_shadows_their_admins_change_for_that_instrument():
    user = _user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,))
    assert _reaches(user, ADMIN_A_KEY, (GOLD,), holders=[(BROKER_B_KEY, GOLD)]) is False
    assert _reaches(user, ADMIN_A_KEY, (NIFTY,), holders=[(BROKER_B_KEY, GOLD)]) is True
    assert _reaches(user, BROKER_B_KEY, (GOLD,), holders=[(BROKER_B_KEY, GOLD)]) is True


def test_clearing_your_last_row_still_reaches_your_users():
    """The actor's OWN key is excluded from the shadow slice on purpose: the
    actor still appears in `holders` while the row exists, and if that
    counted against them, deleting the last row would notify nobody —
    exactly the people whose chart just went blank."""
    user = _user(admin=ADMIN_A)
    assert (
        _reaches(user, ADMIN_A_KEY, (GOLD,), holders=[(ADMIN_A_KEY, GOLD), (SUPER_KEY, GOLD)])
        is True
    )


# ── visibility ───────────────────────────────────────────────────────
def test_a_user_with_lines_switched_off_is_not_told():
    off = SimpleNamespace(enabled=False, locked=False)
    on = SimpleNamespace(enabled=True, locked=False)
    user = _user(admin=ADMIN_A)
    assert _reaches(user, SUPER_KEY, vis={ADMIN_A_KEY: off}) is False
    assert _reaches(user, SUPER_KEY, vis={ADMIN_A_KEY: on}) is True


def test_a_locked_off_row_beats_a_nearer_on_row():
    """Mirrors `_decide_visibility`: a locked row is the super admin's
    decision about that tier, so a broker cannot switch themselves back on
    and start receiving these."""
    user = _user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,))
    vis = {
        BROKER_B_KEY: SimpleNamespace(enabled=True, locked=False),
        ADMIN_A_KEY: SimpleNamespace(enabled=False, locked=True),
    }
    assert _reaches(user, SUPER_KEY, vis=vis) is False


# ── the things that make it safe to run on 700 people ────────────────
def test_it_writes_a_bell_row_and_does_not_make_phones_talk():
    """`user:{id}:notification` is handled by UserWsBridge.tsx:241, which
    raises an OS tray notification through the service worker, plays a
    sound, and reads the message aloud. Publishing there would have made a
    one-price edit announce itself on every connected terminal."""
    src = inspect.getsource(notify_levels_changed)
    assert "Notification.insert_many" in src, "the bell row is the whole point"
    for banned in ("publish_batch", ":notification", "push_service", "send_to_users"):
        assert banned not in src, f"this would reach the noisy client path: {banned!r}"


def test_an_empty_token_set_announces_nothing():
    assert "if not tokens:" in inspect.getsource(notify_levels_changed)
    assert _reaches(_user(admin=ADMIN_A), SUPER_KEY, ()) is False


def test_the_cooldown_is_claimed_only_once_there_is_something_to_send():
    """Burning the gate before the recipient set is known meant a save that
    reached nobody silenced the next ten minutes of real changes."""
    fn = ast.parse(textwrap.dedent(inspect.getsource(notify_levels_changed))).body[0]
    src = ast.unparse(fn)
    assert "nx=True" in src, "the gate must be set-if-absent, not read-then-write"
    assert src.index("recipients =") < src.index("nx=True"), (
        "the cooldown is still claimed before the recipients are resolved"
    )


def test_every_trading_role_is_a_candidate():
    """MASTER and DEALER trade and see charts too — CLIENT alone was wrong."""
    assert "_CHART_ROLES" in inspect.getsource(notify_levels_changed)
    assert set(_CHART_ROLES) == {"CLIENT", "DEALER", "MASTER"}


def test_demo_and_non_active_users_are_excluded():
    src = inspect.getsource(notify_levels_changed)
    assert "UserStatus.ACTIVE" in src
    assert "is_demo" in src


def test_the_super_admin_is_not_narrowed_to_their_own_book():
    """`_pool_clause` answers 'my own clients' for a super admin, which is
    the wrong question — their row is the platform row at the end of
    everyone's cascade, so their reach is everyone."""
    src = inspect.getsource(notify_levels_changed)
    assert "SUPER_ADMIN" in src[: src.index("_pool_clause")]


def test_owner_key_round_trips_the_cascade():
    chain = _owner_cascade(_user(admin=ADMIN_A, broker=BROKER_B, ancestry=(BROKER_B,)))
    assert [_owner_key(f) for f in chain] == [BROKER_B_KEY, ADMIN_A_KEY, SUPER_KEY]


# ── one notification per real change, not per click ──────────────────
def test_every_write_endpoint_gates_on_a_change_and_passes_its_tokens():
    """700 bell rows is not the price of a misclick, and the fan-out cannot
    do per-instrument shadowing without knowing which instruments moved."""
    for fn, gate in (
        (api.import_levels, 'result.get("updated") or result.get("cleared")'),
        (api.clear_levels, "if removed:"),
        (api.save_levels, 'result.get("changed")'),
    ):
        src = inspect.getsource(fn)
        assert "_announce(admin, " in src, f"{fn.__name__} announces without tokens"
        assert gate in src, f"{fn.__name__} announces without gating on {gate!r}"


def test_save_levels_reports_the_third_state():
    """`_upsert` answers saved / cleared / nothing-to-do, and `bool()` folds
    the last two together. `changed` is what keeps 'I pressed Save on a
    blank row' from reading as a real clear."""
    assert '"changed": saved is not None' in inspect.getsource(save_levels)


def test_the_import_reports_cleared_instruments_too():
    """`touched` holds only the saved ones — it feeds the off-screen price
    check. An instrument the sheet CLEARED is just as much a change to the
    person whose chart it vanishes from."""
    src = inspect.getsource(import_workbook)
    assert "changed_tokens.append(token)" in src
    assert src.index("changed_tokens.append(token)") < src.index("if n_saved:"), (
        "cleared instruments must be collected before the saved/cleared split"
    )


def test_the_fanout_task_is_held_until_it_finishes():
    """`asyncio.create_task` keeps only a weak reference, so an unreferenced
    fire-and-forget task can be collected mid-flight and the fan-out would
    just stop, with nothing logged."""
    src = inspect.getsource(api)
    assert "_announcements" in src
    assert "add_done_callback" in src
