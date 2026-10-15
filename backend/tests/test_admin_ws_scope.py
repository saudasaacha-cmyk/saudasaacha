"""Who the `admin:events` socket delivers to.

The hub used to route by a constant (`_SINGLE_KEY = "_all"`) and
`admin_ws` attached SUPER_ADMIN, ADMIN and BROKER sockets to that one
key, so every admin socket received every tenant's events. The payloads
are not scope-free — deposit submit carries `user_name`, `user_code` and
`amount` — and the filtering lived in the browser, so any sub-admin or
broker with DevTools open could watch the whole platform's clients and
deposit amounts go past. Every REST scope fix in this audit was bypassed
by the socket next to it.

Three halves have to agree or the fix is worse than the bug: the publisher
stamps the audience, the hub routes on it, and the handler attaches under
keys that are actually in those stamps. An attach key nothing routes to is
a SILENT failure — it reads as "the admin page stopped refreshing".

Pure: `_route_keys`, `attach` and `_scope_keys` need no Mongo and no
Redis, and the two collaborators `publish_admin_event` calls are
module-level names, so they stub out.

    pytest -q backend/tests/test_admin_ws_scope.py
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.api.ws import admin_ws
from app.core.ws_hub import AdminEventHub
from app.models.user import UserRole
from app.services import admin_events

CHANNEL = "admin:events"

# Two tenants, one broker tree each.
ADMIN_A, ADMIN_X = "admin_a", "admin_x"
BROKER_B1, BROKER_B2 = "broker_b1", "broker_b2"


def _published(payload, *, owners=(), event_type="deposit_update"):
    """Run `publish_admin_event` with Redis and the owner lookup stubbed,
    and return the body that would have gone on the wire."""
    sent: list[dict] = []

    async def fake_publish(channel, body):
        assert channel == admin_events.ADMIN_CHANNEL
        sent.append(body)

    async def fake_owners(subject):
        return list(owners)

    real_publish = admin_events.publish
    real_owners = admin_events._compute_recipient_admin_ids
    admin_events.publish = fake_publish
    admin_events._compute_recipient_admin_ids = fake_owners
    try:
        asyncio.run(admin_events.publish_admin_event(event_type, payload))
    finally:
        admin_events.publish = real_publish
        admin_events._compute_recipient_admin_ids = real_owners
    assert len(sent) == 1
    return sent[0]


def test_the_hub_routes_a_stamped_body_to_its_tenant_only():
    """The leak in one assert, publisher left out of it. `user/wallet.py`
    already stamped this field and the hub ignored it, returning the one
    constant key every socket joined."""
    hub = AdminEventHub()
    body = {"type": "deposit_update", "recipient_admin_ids": [ADMIN_A, BROKER_B1]}

    # Keys spelled out rather than read off the class: this is the one
    # test that has to fail on the ROUTE, not on a missing constant.
    assert set(hub._route_keys(CHANNEL, body)) == {"_super", ADMIN_A, BROKER_B1}
    assert "_all" not in hub._route_keys(CHANNEL, body)


def test_a_deposit_submit_never_reaches_another_tenants_socket():
    """The leak, end to end. Admin A's client submits a deposit; the body
    carries the client's name, code and amount. Admin X is attached, and
    the only keys the hub hands that body are A's and the platform's."""
    hub = AdminEventHub()
    body = _published(
        {
            "event": "submitted",
            "user_id": "client_of_a",
            "user_name": "Ramesh Kumar",
            "user_code": "SS1042",
            "amount": "50000",
        },
        owners=[ADMIN_A, BROKER_B1],
    )

    keys = hub._route_keys(CHANNEL, body)

    # "client_of_a" rides along because the subject is always in its own
    # audience (see `_SUBJECT_FIELDS`); no admin socket keys on a client id,
    # so it routes to nobody. What matters is that X's key is absent.
    assert {hub.SUPER_KEY, ADMIN_A, BROKER_B1} <= set(keys)
    assert ADMIN_X not in keys
    assert BROKER_B2 not in keys
    # The old behaviour in one assert: the key every socket joins must not
    # be in the route, or scoping it was theatre.
    assert hub.BROADCAST_KEY not in keys


def test_the_publisher_scopes_a_payload_that_never_asked_to_be_scoped():
    """Two dozen call sites pass a bare `user_id` and nothing else. The
    point of resolving at the chokepoint is that they stay untouched and
    still get an audience."""
    body = _published({"event": "fill", "user_id": "client_of_a"}, owners=[ADMIN_A])

    assert ADMIN_A in body["recipient_admin_ids"]
    assert ADMIN_X not in body["recipient_admin_ids"]
    assert body["type"] == "deposit_update"  # body shape otherwise unchanged
    assert body["event"] == "fill"


def test_an_explicit_recipient_list_is_left_alone():
    """`user/wallet.py` and `notification_service.py` already compute the
    audience for their push fan-out. Recomputing it would be a second
    source of truth, and overwriting a shorter list would widen it."""
    body = _published(
        {"user_id": "client_of_a", "recipient_admin_ids": [ADMIN_A]},
        owners=[ADMIN_A, ADMIN_X, BROKER_B1],
    )

    assert body["recipient_admin_ids"] == [ADMIN_A]


def test_an_event_about_a_broker_includes_that_broker():
    """`pnl_sharing_update` names a `broker_id`, not a user. Owners-only
    would be everyone ABOVE the broker — the one party the event is
    actually about would be the one that never hears it."""
    body = _published(
        {"broker_id": BROKER_B2},
        owners=[ADMIN_A, BROKER_B1],
        event_type="pnl_sharing_update",
    )

    assert set(body["recipient_admin_ids"]) == {ADMIN_A, BROKER_B1, BROKER_B2}


def test_an_event_about_an_admin_includes_that_admin():
    """`branding_domain_ready` carries only `admin_id` — same shape."""
    body = _published(
        {"admin_id": ADMIN_X, "domain": "x.example.com"},
        owners=[],
        event_type="branding_domain_ready",
    )

    assert body["recipient_admin_ids"] == [ADMIN_X]


def test_an_operators_own_wallet_move_reaches_that_operator():
    """`wallet_service` names every subject `user_id`, trader or not: a P&L
    sharing settlement debits the broker and credits the admin BY ID, so the
    payload is `{"user_id": <operator id>}`. The owner resolver only returns
    who is ABOVE that row, so treating `user_id` as "always a trader" leaves
    the operator whose money just moved off its own audience — their wallet
    tile then silently stops refreshing while everyone above them updates."""
    body = _published(
        {"user_id": BROKER_B1, "reason": "PNL_SHARING_PAYOUT", "amount": "-12500"},
        owners=[ADMIN_A],
        event_type="wallet_update",
    )

    assert set(body["recipient_admin_ids"]) == {ADMIN_A, BROKER_B1}

    hub = AdminEventHub()
    sock = object()
    hub.attach(sock, _keys(UserRole.BROKER, BROKER_B1))
    assert sock in {s for k in hub._route_keys(CHANNEL, body) for s in hub._subscribers.get(k, ())}


def test_an_empty_explicit_recipient_list_is_not_trusted():
    """`user/wallet.py` seeds `recipient_ids = []` before a try/except round
    its owner lookup. A blip there used to broadcast; trusting the empty list
    would route to super-admins only and leave the owning admin's Deposits
    inbox stale. Re-resolve from `user_id` instead — same answer when the
    lookup works, broadcast when it doesn't."""
    body = _published(
        {"user_id": "client_of_a", "recipient_admin_ids": []},
        owners=[ADMIN_A, BROKER_B1],
    )

    assert ADMIN_A in body["recipient_admin_ids"]
    assert BROKER_B1 in body["recipient_admin_ids"]


def test_an_unscopeable_event_broadcasts_rather_than_vanishing():
    """A payload with no subject gets no stamp, and the hub falls back to
    the key every socket joins. Deliberate: an event that reaches one
    admin too many costs a refetch, one that reaches nobody looks exactly
    like the staleness bug this channel exists to fix. No current emitter
    takes this path — `publish_admin_event` logs when one does."""
    hub = AdminEventHub()
    body = _published({"note": "platform wide"}, event_type="something_new")

    assert "recipient_admin_ids" not in body
    assert hub._route_keys(CHANNEL, body) == [hub.BROADCAST_KEY]


def test_a_foreign_channel_is_still_dropped():
    hub = AdminEventHub()
    assert hub._route_keys("market:tick:256265", {"recipient_admin_ids": [ADMIN_A]}) == []


# ── attach: the keys have to be the ones the publisher stamps ──────────


def _keys(role, user_id, broker_ids=()):
    """`_scope_keys` for one role, with the broker-pool query stubbed."""
    user = SimpleNamespace(role=role, id=user_id)

    class _Coll:
        def find(self, *_a, **_k):
            async def gen():
                for b in broker_ids:
                    yield {"_id": b}

            return gen()

    real = admin_ws.User.get_motor_collection
    admin_ws.User.get_motor_collection = staticmethod(_Coll)
    try:
        return asyncio.run(admin_ws._scope_keys(user))
    finally:
        admin_ws.User.get_motor_collection = real


def test_a_super_admin_keeps_the_whole_platform():
    """Its own id is a recipient ONLY for platform-direct users, so keying
    on it would hide every event inside an admin's or broker's tree."""
    hub = AdminEventHub()
    assert _keys(UserRole.SUPER_ADMIN, "super_1") == [hub.SUPER_KEY]
    assert hub.SUPER_KEY in hub._route_keys(CHANNEL, {"recipient_admin_ids": [ADMIN_A]})


def test_a_broker_reads_its_own_id_not_its_parent_admins():
    """A broker's id is in every descendant's `broker_ancestry`, which is
    what the owner resolver returns — so one key covers the whole subtree
    and the parent admin's key would be both wrong and wider."""
    assert _keys(UserRole.BROKER, BROKER_B1) == [BROKER_B1]

    hub = AdminEventHub()
    sock = object()
    hub.attach(sock, _keys(UserRole.BROKER, BROKER_B1))
    sub_client = {"recipient_admin_ids": [ADMIN_A, BROKER_B1, BROKER_B2]}
    assert sock in {s for k in hub._route_keys(CHANNEL, sub_client) for s in hub._subscribers.get(k, ())}


def test_an_admin_also_attaches_to_the_brokers_in_its_pool():
    """A BROKER transferred in keeps its descendants' stale
    `assigned_admin_id`, which is why `_admin_pool_clause` has a broker
    arm. Without the same arm here the socket goes quiet for an entire
    subtree the Users page still lists."""
    assert _keys(UserRole.ADMIN, ADMIN_X, [BROKER_B2]) == [ADMIN_X, BROKER_B2]

    hub = AdminEventHub()
    sock = object()
    hub.attach(sock, _keys(UserRole.ADMIN, ADMIN_X, [BROKER_B2]))
    # Client still stamped with the OLD admin, reached via the broker arm.
    stale = {"recipient_admin_ids": [ADMIN_A, BROKER_B2]}
    assert sock in {s for k in hub._route_keys(CHANNEL, stale) for s in hub._subscribers.get(k, ())}


def test_detach_clears_every_key_the_socket_sat_on():
    """A socket now sits on several keys. Dropping it from one of them
    leaves the hub writing to a closed connection on the others."""
    hub = AdminEventHub()
    sock = object()
    hub.attach(sock, [ADMIN_X, BROKER_B2])
    assert hub.subscriber_count() == 3  # broadcast + own id + broker

    hub.detach(sock)

    assert hub.subscriber_count() == 0
