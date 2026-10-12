"""Every `user:{id}:<topic>` a publisher uses must be routable.

`UserChannelHub._route_keys` drops any topic not on its allow-list, and
it drops it SILENTLY: the publisher succeeds, Redis fans the message out,
and no socket receives it. That is how admin broadcasts landed in the
bell icon — the DB row is written separately — while never popping a
toast or ringing. "notification" had simply never been added.

This test scans the publishers rather than listing them by hand, so the
next topic someone invents fails here instead of in production.

    pytest -q backend/tests/test_user_ws_topics.py
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.ws_hub import user_channel_hub

APP = Path(__file__).resolve().parents[1] / "app"
# f"user:{whatever}:topic"
CHANNEL = re.compile(r'f"user:\{[^"}]+\}:([a-z_]+)"')


def published_topics() -> set[str]:
    found: set[str] = set()
    for path in APP.rglob("*.py"):
        found.update(CHANNEL.findall(path.read_text()))
    return found


def test_the_scan_finds_the_publishers_at_all():
    """Guard the guard: a regex that matches nothing would make every
    assertion below vacuously true."""
    topics = published_topics()
    assert {"wallet", "positions", "notification"} <= topics, topics


def test_every_published_topic_is_routable():
    allowed = user_channel_hub._ALLOWED_TOPICS
    missing = sorted(published_topics() - set(allowed))
    assert not missing, (
        f"These topics are published but dropped by the hub: {missing}. "
        "Add them to UserChannelHub._ALLOWED_TOPICS."
    )


def test_admin_broadcasts_reach_a_socket():
    """The specific regression: the channel the broadcast endpoint
    publishes on has to resolve to the recipient's socket."""
    assert user_channel_hub._route_keys("user:abc123:notification", {}) == ["abc123"]


def test_an_unknown_topic_is_still_dropped():
    """The allow-list is a filter, not decoration — a typo'd channel
    must not fan out to a user's socket."""
    assert user_channel_hub._route_keys("user:abc123:bogus", {}) == []
    assert user_channel_hub._route_keys("user:abc123", {}) == []
    assert user_channel_hub._route_keys("admin:events", {}) == []
