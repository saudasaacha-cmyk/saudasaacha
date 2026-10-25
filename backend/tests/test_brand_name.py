"""The brand name is configuration, not a literal.

This platform has now been renamed three times — SaudaSaacha, then
SachchaSauda, then RIZING BULL — and each pass found code that had
quietly baked the name of the day into something a user sees. The
expensive ones are never the page copy, which is obvious the moment you
look at it; they are the derived strings nobody re-reads.

Report filenames are the worked example. They were hard-coded, so after
the first rename every customer downloaded files stamped with the brand
that no longer existed. The fix derived them from `APP_NAME` — but took
only the first word, to drop the "Broker" suffix that brand carried, and
so truncated the next brand, whose name is two words, to "rizing".

    pytest -q backend/tests/test_brand_name.py
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

from app.api.v1.user.reports import _brand_slug
from app.core.config import settings

APP = pathlib.Path(__file__).resolve().parent.parent / "app"


@pytest.mark.parametrize(
    "app_name, expected",
    [
        ("RIZING BULL", "rizing_bull"),
        ("SachchaSauda Broker", "sachchasauda_broker"),
        ("Rizing  Bull   Pvt. Ltd.", "rizing_bull_pvt_ltd"),
        ("", "report"),
        ("   ", "report"),
        ("!!!", "report"),
    ],
)
def test_the_whole_brand_survives_into_the_filename(monkeypatch, app_name, expected):
    """Every word of it. A two-word brand losing its second word is how
    this last went wrong, and it is invisible until someone opens their
    downloads folder."""
    monkeypatch.setattr(settings, "APP_NAME", app_name)
    assert _brand_slug() == expected


@pytest.mark.parametrize(
    "app_name", ["RIZING BULL", "Brand/../../etc", 'Quote"Brand', "Brand\r\nX"]
)
def test_the_slug_is_safe_to_put_in_a_filename(monkeypatch, app_name):
    """It lands in a Content-Disposition header, so anything outside
    [a-z0-9_] is a header injection or a broken download waiting to
    happen. APP_NAME comes from the environment, which on a white-label
    box is set per deploy rather than audited."""
    monkeypatch.setattr(settings, "APP_NAME", app_name)
    assert re.fullmatch(r"[a-z0-9_]+", _brand_slug())


# Where the name is allowed to appear as a literal:
#   config.py    — the definition of APP_NAME itself.
#   security.py  — the TOTP issuer's default argument, the backstop for a
#                  caller that passes nothing. Every real caller passes
#                  settings.APP_NAME.
BRAND_LITERAL_EXEMPT = {"core/config.py", "core/security.py"}


def test_no_brand_literal_is_baked_into_backend_code():
    """`APP_NAME` is env-tunable precisely so one deploy can be RIZING
    BULL while a white-label tenant is something else. A literal in a
    service defeats that for every tenant at once — which is how the PDF
    reports came to print the platform's name on a tenant's statement,
    and how 2FA enrolment stamped it into every authenticator app.

    Docstrings and comments are prose and exempt; this walks the AST so
    they are excluded by structure rather than by a regex that a line
    break would defeat.
    """
    offenders = []
    for path in APP.rglob("*.py"):
        rel = str(path.relative_to(APP))
        if rel in BRAND_LITERAL_EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            id(n.body[0].value)
            for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and n.body
            and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
            and isinstance(n.body[0].value.value, str)
        }
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and re.search(r"\bRIZING BULL\b", node.value, re.I)
            ):
                offenders.append(f"{rel}:{node.lineno}: {node.value[:60]!r}")
    assert not offenders, "brand name hard-coded:\n" + "\n".join(offenders)


def test_a_placeholder_address_is_recognised_across_renames():
    """Rows written under an older brand still carry its `@noemail.<old>`
    host. Matching only the CURRENT one would make every one of those
    look like a real address the moment the brand moved."""
    from app.services.user_service import NO_EMAIL_DOMAIN, is_placeholder_contact

    assert NO_EMAIL_DOMAIN.startswith("noemail.")
    assert is_placeholder_contact(f"ab1234@{NO_EMAIL_DOMAIN}")
    assert is_placeholder_contact("ab1234@noemail.sachchasauda.com")
    assert is_placeholder_contact("ab1234@noemail.marginplant.com")
    assert not is_placeholder_contact("someone@gmail.com")
