"""What we are allowed to put in a Web Push title and body.

Chrome runs an on-device spam classifier over every Android notification's
title and body. A flagged one is replaced by "Possible spam" carrying an
Unsubscribe button that REVOKES the site's notification permission
outright — so one bad-looking push does not just fail, it costs that user
every future push until they re-grant by hand.

This bit us for real on 2026-10-15: an admin broadcast titled "Important
Update for Deposit", body "…Scan the QR / Make payment / Send screenshot
of payment done", blasted to 674 users in 15 ms from a days-old domain.
Chrome flagged it, and it was not wrong to — that text is indistinguishable
from the QR payment scams it exists to catch.

Two rules fall out of that, and both are pinned here because both are one
careless commit away from coming back:

  * no emoji in anything a push path can send — a money emoji in a title
    is one of the loudest signals the classifier has;
  * the payment-details alert says one thing to the bell and a quieter
    thing to the push, because the honest wording ("the account changed,
    use the new details before you send money") is the exact shape of a
    payment-redirection fraud.

    pytest -q backend/tests/test_push_copy_not_spam_shaped.py
"""

from __future__ import annotations

import ast
import inspect
import pathlib
import re

from app.services.notification_service import notify_payment_details_changed

APP = pathlib.Path(__file__).resolve().parent.parent / "app"

# Pictographs, dingbats, arrows-with-presentation, and the variation
# selector that turns a bare glyph into one. Deliberately broad: the point
# is to make someone stop and think, not to be a precise emoji parser.
EMOJI = re.compile(
    "[\U0001f300-\U0001faff"
    "\U00002600-\U000027bf"
    "\U00002b00-\U00002bff"
    "\U0000fe0f]"
)

# A file is in scope when it can reach a push send. Scoping to these rather
# than the whole tree keeps the rule where it means something — an emoji in
# a PDF heading harms nobody.
PUSH_MARKERS = ("push_service", "_push_user", "_push_owners", "send_to_user")


def _push_files() -> list[pathlib.Path]:
    out = []
    for path in APP.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(m in text for m in PUSH_MARKERS):
            out.append(path)
    return out


def test_the_scan_actually_covers_the_files_that_send_push():
    """A guard on the guard: if the markers stop matching, every assertion
    below passes over an empty list and proves nothing."""
    files = _push_files()
    names = {p.name for p in files}
    assert len(files) >= 4, files
    # The four known senders at the time of writing. If one is renamed,
    # fix this list — do not delete the assertion.
    assert {"wallet_service.py", "payin_out.py", "wallet.py", "notification_service.py"} <= names


def test_no_emoji_in_any_string_a_push_file_can_send():
    """Checked over AST string constants, not raw source, so the docstrings
    and comments explaining WHY the emoji are gone do not fail the rule
    they are explaining."""
    offenders: list[str] = []
    for path in _push_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        doc_nodes = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    doc_nodes.add(id(body[0].value))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in doc_nodes
                and EMOJI.search(node.value)
            ):
                offenders.append(f"{path.name}:{node.lineno}: {node.value[:60]!r}")
    assert not offenders, (
        "Emoji in a push-capable string. A money or warning emoji in a push "
        "title is a loud spam signal to Chrome's classifier, and a flagged "
        "push can cost the user's notification permission outright:\n  "
        + "\n  ".join(offenders)
    )


def test_the_payment_alert_says_less_to_the_push_than_to_the_bell():
    """The bell keeps the real warning; the push only has to get them into
    the app. If these two ever become the same string again, the honest
    wording goes back out over the channel that is being read by a fraud
    classifier."""
    src = inspect.getsource(notify_payment_details_changed)
    assert "push_body" in src, "the push lost its own copy"
    assert "body=push_body" in src, "the push is being sent the bell's wording again"

    tree = ast.parse(ast.unparse(ast.parse(src)))
    pushed = {
        n.targets[0].id: n.value.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and isinstance(n.value, ast.Constant)
        and isinstance(n.value.value, str)
    }
    body = pushed.get("push_body", "")
    assert body, "push_body is no longer a plain literal — check this test still bites"

    # The phrases that make it read like a payment-redirection scam. The
    # bell copy is allowed to use them; the push is not.
    low = body.lower()
    for banned in ("sending any money", "send money", "before you pay", "scan", "qr", "urgent", "important"):
        assert banned not in low, f"push copy contains scam-shaped phrase {banned!r}: {body!r}"
    # It must still be actionable, or the alert is pointless.
    assert "app" in low or "open" in low, body


def test_the_bell_still_carries_the_real_warning():
    """The softening is for the push ONLY. Someone wiring money to a closed
    account is the failure this whole alert exists to prevent, so the
    explicit sentence has to survive somewhere the user will read it."""
    src = inspect.getsource(notify_payment_details_changed)
    assert "before sending any money" in src, "the real warning was softened away entirely"
    # ...and it is what the Notification row and the socket get.
    assert "message=message" in src or "title=title" in src
