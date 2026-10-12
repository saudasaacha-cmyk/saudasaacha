"""Per-category notification tones, and who hears a payment-details change.

Three categories rather than one per event type: a user should be able
to tell from the sound alone whether money ARRIVED or whether the
details for SENDING money changed — those are very different pieces of
news and the second one is how people lose deposits to a stale account.

    pytest -q backend/tests/test_notify_sounds.py
"""

from __future__ import annotations

import inspect

from app.api.v1.user.support import _SOUND_DEFAULTS, get_notify_sounds
from app.services.notification_service import notify_payment_details_changed


def test_the_three_categories_are_the_ones_the_client_asks_for():
    assert set(_SOUND_DEFAULTS) == {"general", "money", "payment"}


def test_every_category_has_a_distinct_default():
    """A deployment that never opens the settings page still gets three
    tones a user can tell apart."""
    assert len(set(_SOUND_DEFAULTS.values())) == 3


def test_the_defaults_match_what_the_seed_writes():
    """Otherwise the endpoint's fallback and the stored row disagree, and
    the tone changes the first time someone saves an unrelated setting."""
    seed = (
        inspect.getsource(__import__("app.seed.seed_data", fromlist=["x"]))
    )
    for category, tone in _SOUND_DEFAULTS.items():
        assert f'"notify.sound_{category}"' in seed
        block = seed[seed.index(f'"notify.sound_{category}"') :][:200]
        assert f'"{tone}"' in block, f"{category} default drifted from the seed"


def test_a_missing_or_blank_row_falls_back_rather_than_going_silent():
    src = inspect.getsource(get_notify_sounds)
    # An empty stored value must not become an empty tone id.
    assert 'or fallback' in src


def test_payment_alerts_reach_only_the_actors_own_pool():
    """A broker's client deposits into the BROKER's account, so an admin
    above them changing theirs is not news that client can act on."""
    src = inspect.getsource(notify_payment_details_changed)
    assert 'query["assigned_admin_id"] = None' in src      # super admin's direct pool
    assert 'query["assigned_broker_id"] = actor.id' in src  # broker's own clients
    assert 'query["assigned_admin_id"] = actor.id' in src   # sub-admin's own clients
    # Only active clients — not other admins, not closed accounts.
    assert "UserRole.CLIENT" in src
    assert "UserStatus.ACTIVE" in src


def test_the_payment_alert_carries_its_category():
    """Without the tag the client would play the ordinary tone and the
    whole point of a separate sound is lost."""
    src = inspect.getsource(notify_payment_details_changed)
    assert '"category": "payment"' in src
    assert '"type": "notification"' in src


def test_each_category_falls_through_on_its_own():
    """A broker who set only the payment tone keeps inheriting the other
    two. Resolving as a block would silently reset them."""
    from app.api.v1.user.support import get_notify_sounds as fn

    src = inspect.getsource(fn)
    body = src[src.index("for category, fallback"):]
    # The owner walk happens INSIDE the per-category loop.
    assert "for owner in owners" in body
    assert "break" in body


def test_the_cascade_is_broker_then_admin_then_platform():
    from app.api.v1.user.support import get_notify_sounds as fn

    src = inspect.getsource(fn)
    i_broker = src.index("broker_ancestry")
    i_admin = src.index("assigned_admin_id")
    i_platform = src.index("_read_setting")
    assert i_broker < i_admin < i_platform


def test_a_super_admin_is_pushed_to_the_platform_rows():
    """Writing a personal override would leave the row everyone else
    inherits untouched while looking like it had changed."""
    from app.api.v1.admin.settings import set_my_notify_sounds

    src = inspect.getsource(set_my_notify_sounds)
    assert "UserRole.SUPER_ADMIN" in src
    assert "status_code=400" in src


def test_clearing_an_override_stores_null_not_an_empty_string():
    """None means inherit. An empty string stored instead would resolve
    to falsy too, but it reads as "set to nothing" in the database and
    the admin UI would show it as a real choice."""
    from app.api.v1.admin.settings import set_my_notify_sounds

    src = inspect.getsource(set_my_notify_sounds)
    assert 'or None' in src
