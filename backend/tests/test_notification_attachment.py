"""An attached image is OUR file, and a small one.

The broadcast pushes this path to every phone in a pool, so the field is not
a free URL: a remote address would let one admin load — or track — anything
inside everyone's app, and a `..` in the name would walk off the uploads
directory. The size cap is the other half: a notification is read on a
phone, often on mobile data.

    pytest -q backend/tests/test_notification_attachment.py
"""

from __future__ import annotations

from app.api.v1.admin.notifications import (
    ALLOWED_NOTIF_IMAGE,
    MAX_NOTIF_IMAGE_BYTES,
    is_own_attachment,
)


def test_a_path_we_wrote_is_accepted():
    assert is_own_attachment("/uploads/notifications/notif-6acb3ecf-1762500000000.png")
    assert is_own_attachment("/uploads/notifications/notif-1.webp")


def test_a_remote_address_is_not():
    assert not is_own_attachment("https://evil.example/tracker.png")
    assert not is_own_attachment("//evil.example/x.png")
    assert not is_own_attachment("/uploads/logos/logo-1.png")


def test_traversal_and_empties_are_not():
    assert not is_own_attachment("/uploads/notifications/../../etc/passwd")
    assert not is_own_attachment("/uploads/notifications/")
    assert not is_own_attachment("")
    assert not is_own_attachment(None)  # type: ignore[arg-type]


def test_the_limit_is_two_megabytes_and_three_image_types():
    assert MAX_NOTIF_IMAGE_BYTES == 2 * 1024 * 1024
    assert set(ALLOWED_NOTIF_IMAGE) == {"image/png", "image/jpeg", "image/webp"}
    # No SVG: it is a script container, and this one is rendered in every
    # user's app rather than in the admin's own.
    assert "image/svg+xml" not in ALLOWED_NOTIF_IMAGE
