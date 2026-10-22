"""Whose support WhatsApp number a user is shown.

The number cascades UP the assignment chain: the user's own row, then
their broker, then their admin. What it could not do — and this is the
bug — is reach the SUPER ADMIN.

`_resolve_whatsapp_for_user` walks `assigned_broker_id or
assigned_admin_id` and stops at the first node where both are None. That
is true of every admin, and it is true of the super admin, so a number
typed into the super admin's own Support page was written to their User
row (`admin/support.py` sets `user_doc.support_whatsapp`) and read by
nobody. A super admin's own clients hit it immediately, since
`assigned_admin_id is None` is exactly what marks a client as theirs.

The platform-wide `platform.support_whatsapp` PlatformSetting is a
DIFFERENT field on a different page, which is why "I set it and nothing
happened" was the symptom rather than an error.

    pytest -q backend/tests/test_support_whatsapp_cascade.py
"""

from __future__ import annotations

import ast
import inspect
import textwrap

from app.api.v1.user import support


def _fn_source(name: str) -> str:
    return textwrap.dedent(inspect.getsource(getattr(support, name)))


def test_the_walk_terminates_where_the_bug_was():
    """Pins the mechanism, so the fallback below is not mistaken for
    belt-and-braces. The walk genuinely cannot climb past a node with no
    broker and no admin — which is every admin, and the super admin."""
    src = _fn_source("_resolve_whatsapp_for_user")
    assert "cur.assigned_broker_id or cur.assigned_admin_id" in src
    assert "if next_id is None" in src


def test_there_is_a_super_admin_fallback():
    assert hasattr(support, "_super_admin_whatsapp")
    src = _fn_source("_super_admin_whatsapp")
    assert "SUPER_ADMIN" in src
    assert "support_whatsapp" in src


def test_the_fallback_runs_before_the_platform_setting():
    """Order matters. The Platform Settings row predates per-admin numbers
    and its own comment calls itself the last resort; the Support page is
    the newer, more specific mechanism, so a number typed there must win
    over one left behind in the old global setting."""
    src = _fn_source("contacts") if hasattr(support, "contacts") else inspect.getsource(support)
    assert "_super_admin_whatsapp()" in src
    assert "platform.support_whatsapp" in src
    assert src.index("_super_admin_whatsapp()") < src.index('_read_setting("platform.support_whatsapp")')


def test_the_fallback_only_fires_when_the_walk_found_nothing():
    """An admin who HAS set a number must keep it — the super admin's is
    a fallback, not an override. Checked on the AST so the comment
    explaining the order does not satisfy the assertion."""
    tree = ast.parse(inspect.getsource(support))
    calls_under_if = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_super_admin_whatsapp"
            ):
                calls_under_if.append(ast.unparse(node.test))
    assert calls_under_if, "the fallback is called unconditionally"
    assert any("whatsapp" in t for t in calls_under_if), calls_under_if


def test_the_lookup_is_deterministic():
    """Two SUPER_ADMIN rows must not mean two different answers depending
    on what Mongo returned first."""
    assert "sort(" in _fn_source("_super_admin_whatsapp")
