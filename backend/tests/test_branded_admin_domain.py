"""The admin panel on a tenant's own domain: admin.<domain>.

Five places have to agree on that hostname — the DNS check, the DNS
preview the UI renders, the provisioning helper's nginx block, the
certbot name list and the CORS allow-list — so it comes from one
function. The riskiest part is the certbot call: asking for a name
whose A record is missing fails the WHOLE certificate, taking the
trading app down with it, so the admin host is strictly optional.

    pytest -q backend/tests/test_branded_admin_domain.py
"""

from __future__ import annotations

import inspect
from pathlib import Path

from app.services.branding_service import admin_host_for

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "deploy/scripts/saudasaacha-add-branded-domain.sh"
)


def test_the_admin_host_is_one_definition():
    assert admin_host_for("risingbull.live") == "admin.risingbull.live"
    # Normalised the same way the rest of the branding code normalises.
    assert admin_host_for("  RisingBull.LIVE ") == "admin.risingbull.live"
    assert admin_host_for(".example.com") == "admin.example.com"


def test_the_dns_preview_reports_on_the_admin_host():
    """The UI renders a row per key, so a missing key is a missing row."""
    from app.services import branding_service

    src = inspect.getsource(branding_service.resolve_dns_preview)
    assert '"admin"' in src
    assert "admin_host_for" in src


def test_the_helper_serves_the_admin_panel_on_its_own_port():
    """3001, not 3000 — the user app and the admin app are separate
    Next servers and swapping them would hand clients the admin panel."""
    body = SCRIPT.read_text()
    assert "server_name admin.${DOMAIN};" in body
    assert "ADMIN_PORT=\"${SACHCHASAUDA_ADMIN_PORT:-3001}\"" in body
    assert "proxy_pass http://127.0.0.1:${ADMIN_PORT};" in body


def test_the_admin_name_is_only_requested_when_asked_for():
    """Both the nginx block and the certbot name sit behind the same
    flag. certbot fails the entire certificate on a name it cannot
    validate, so a tenant who hasn't pointed admin.<domain> must still
    get a working trading app."""
    body = SCRIPT.read_text()
    assert body.count('if [[ "$WITH_ADMIN" == "with-admin" ]]; then') == 2
    assert 'CERT_NAMES+=(-d "admin.${DOMAIN}")' in body
    # …and the two always-present names are never behind the flag.
    assert 'CERT_NAMES=(-d "$DOMAIN" -d "www.${DOMAIN}")' in body


def test_provisioning_asks_dns_before_adding_the_admin_name():
    from app.workers import branding_tasks

    src = inspect.getsource(branding_tasks.run_provisioning)
    assert "admin_host_resolves" in src
    assert 'cmd.append("with-admin")' in src


def test_removal_takes_the_admin_block_with_it():
    """Both server blocks live in ONE conf file, so deleting the file
    removes the admin host too — no separate cleanup to forget."""
    add = SCRIPT.read_text()
    remove = (SCRIPT.parent / "saudasaacha-remove-branded-domain.sh").read_text()
    assert 'CONF_NAME="sachchasauda-branded-${DOMAIN}.conf"' in add
    assert 'CONF_NAME="sachchasauda-branded-${DOMAIN}.conf"' in remove
    assert 'rm -f "$SYMLINK_PATH" "$CONF_PATH"' in remove


def test_the_admin_host_resolves_to_the_tenant_who_owns_the_domain():
    """admin.<domain> has no row of its own — the tenant saved
    <domain>. Without this the admin login page on a branded host
    greeted the broker's staff with the platform's name."""
    from app.services import branding_service

    src = inspect.getsource(branding_service.find_admin_by_domain)
    assert 'norm.startswith("admin.")' in src
    # Exact match is tried FIRST, so an admin who deliberately saved
    # "admin.foo.com" as their trading host still wins on their own
    # name instead of being handed foo.com's owner.
    assert "candidates = [norm]" in src
