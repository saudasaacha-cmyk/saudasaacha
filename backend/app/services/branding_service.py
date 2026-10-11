"""White-label branding service.

Single source of truth for all branding-related logic:

* Domain normalization + validation.
* Public lookups by ``user_code`` and ``custom_domain``.
* DNS verification (A-record check against ``PLATFORM_PUBLIC_IP``).
* Certbot orchestration handle (the actual subprocess lives in
  ``app.workers.branding_tasks`` so it can run on a Celery worker, not
  in the request thread).
* Logo storage on local disk under ``backend/uploads/logos/``.

Every public function below is a no-op / explicit error when
``settings.BRANDING_ENABLED`` is False, so this module is safe to
import even on Phase-1 deploys where the feature is gated off.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Final

from beanie import PydanticObjectId

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.models.user import User, UserRole, UserStatus
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────
LOGO_DIR: Final[Path] = Path("uploads") / "logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

MAX_LOGO_BYTES: Final[int] = 2 * 1024 * 1024  # 2 MB
ALLOWED_LOGO_MIMES: Final[set[str]] = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/svg+xml",
}
ALLOWED_LOGO_EXTS: Final[dict[str, str]] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

# RFC 1035-ish: lowercase letters/digits/hyphens, dot-separated, 1-63 chars
# per label, total length <= 253. Matches what registrars accept.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}$"
)

# Custom-domain provisioning lifecycle.
STATUS_PENDING_DNS: Final[str] = "PENDING_DNS"
STATUS_DNS_VERIFIED: Final[str] = "DNS_VERIFIED"
STATUS_PROVISIONING: Final[str] = "PROVISIONING"
STATUS_READY: Final[str] = "READY"
STATUS_FAILED: Final[str] = "FAILED"

# Signup-origin tags stamped on User.signup_origin.
ORIGIN_PLATFORM: Final[str] = "PLATFORM"
ORIGIN_BRANDED_REFERRAL: Final[str] = "BRANDED_REFERRAL"
ORIGIN_CUSTOM_DOMAIN: Final[str] = "CUSTOM_DOMAIN"


# ── Helpers ──────────────────────────────────────────────────────────
def _ensure_enabled() -> None:
    if not settings.BRANDING_ENABLED:
        # Caller decides whether to surface a 503 or silently skip; we
        # just raise so it's an explicit decision.
        raise ValidationFailedError(
            "Branding feature is disabled (set BRANDING_ENABLED=true)"
        )


def normalize_domain(raw: str | None) -> str | None:
    """Strip scheme / leading-www / trailing slash + lowercase.

    Returns ``None`` for empty input. Raises ValidationFailedError if
    the result doesn't look like a valid public hostname.
    """
    if raw is None:
        return None
    v = raw.strip().lower()
    if not v:
        return None
    # Strip scheme
    if "://" in v:
        v = v.split("://", 1)[1]
    # Drop path/query
    v = v.split("/", 1)[0].split("?", 1)[0]
    # Drop port
    v = v.split(":", 1)[0]
    # Drop leading www. — we always cover both apex + www in certbot.
    if v.startswith("www."):
        v = v[4:]
    if not _DOMAIN_RE.match(v):
        raise ValidationFailedError(
            f"'{raw}' is not a valid domain (e.g. mybroker.com)"
        )
    return v


def normalize_user_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    v = raw.strip().upper()
    return v or None


def to_branding_payload(admin: User) -> dict:
    """Public-safe branding fields for an admin (used by /by-code,
    /by-domain, /me/branding). Hides any internal/PII data.

    `custom_domain_last_error` is included because the admin-side UI
    needs it to render the FAILED panel inline without a second
    /domain/status call. The string is operator-friendly (DNS error
    messages, certbot stderr summaries) — not sensitive — so it's
    safe to surface even on the public endpoints (they only return
    it when status == FAILED, which is a transient state public
    callers won't typically see anyway).
    """
    return {
        "admin_id": str(admin.id),
        "user_code": admin.user_code,
        "brand_name": admin.brand_name,
        "logo_url": admin.logo_url,
        "telegram_link": admin.telegram_link,
        "custom_domain": admin.custom_domain,
        "custom_domain_status": admin.custom_domain_status,
        "custom_domain_last_error": admin.custom_domain_last_error,
    }


# ── Public lookups ────────────────────────────────────────────────────
async def find_admin_by_user_code(user_code: str) -> User | None:
    """Lookup an ACTIVE ADMIN by their `user_code`. Case-insensitive.

    Returns ``None`` for missing / non-admin / non-active rows so the
    caller can map to a clean 404 without leaking which case hit.
    """
    code = normalize_user_code(user_code)
    if not code:
        return None
    user = await User.find_one(User.user_code == code)
    if user is None or user.role != UserRole.ADMIN or user.status != UserStatus.ACTIVE:
        return None
    return user


async def find_broker_by_user_code(user_code: str) -> User | None:
    """Lookup an ACTIVE BROKER by their `user_code`. Case-insensitive.

    Used for broker referral links so users registering via a broker's
    link are automatically assigned under that broker.
    """
    code = normalize_user_code(user_code)
    if not code:
        return None
    user = await User.find_one(User.user_code == code)
    if user is None or user.role != UserRole.BROKER or user.status != UserStatus.ACTIVE:
        return None
    return user


async def find_platform_super_admin() -> User | None:
    """Return the platform-default super admin so the user app can
    render their branding (logo + brand_name + favicon) when the
    visitor isn't on a specific tenant's domain or referral link.

    Without this, the platform host (sachchasauda.com) had no
    branding source at all — BrandingProvider stayed null and the
    auth screens fell back to the hard-coded SachchaSauda glyph.
    Picking the OLDEST active SUPER_ADMIN matches the bootstrap
    seed's single-super-admin assumption while still being safe in
    multi-super-admin deployments (the founding row wins).
    """
    coll = User.get_motor_collection()
    doc = await coll.find_one(
        {
            "role": UserRole.SUPER_ADMIN.value,
            "status": UserStatus.ACTIVE.value,
        },
        sort=[("created_at", 1)],
    )
    if doc is None:
        return None
    return await User.get(doc["_id"])


async def find_admin_by_domain(domain: str) -> User | None:
    """Lookup an admin by their configured ``custom_domain``.

    Tries exact match first, then strips a leading ``www.`` so requests
    landing on ``www.broker.com`` resolve to the same admin who saved
    ``broker.com``.
    """
    try:
        norm = normalize_domain(domain)
    except ValidationFailedError:
        return None
    if not norm:
        return None

    # Exact first, then with a leading `admin.` removed, so the admin
    # panel on admin.<domain> resolves to the tenant who owns <domain>.
    # Exact-first matters: an admin who deliberately saved
    # "admin.foo.com" as their TRADING host still wins on their own
    # name instead of being redirected to a foo.com that may be
    # somebody else's.
    candidates = [norm]
    if norm.startswith("admin."):
        candidates.append(norm[len("admin.") :])

    for candidate in candidates:
        user = await User.find_one(User.custom_domain == candidate)
        if user is None:
            continue
        if user.role != UserRole.ADMIN or user.status != UserStatus.ACTIVE:
            continue
        return user
    return None


async def brand_domain_for_user(user: User) -> str | None:
    """Return the READY ``custom_domain`` of the admin who owns ``user``
    (via ``assigned_admin_id``), or ``None`` when there is no branded
    domain to land on.

    Used so cross-app handoffs (e.g. admin "Login as user" impersonation)
    open DIRECTLY on the tenant's own host instead of the shared platform
    origin. Landing on the platform first triggers the white-label
    ``#wl=`` redirect, which restores tokens but NOT the auth-store user
    on the destination domain → the terminal guard bounces back to
    ``/login``. Going straight to the branded host avoids that hop.
    """
    if not settings.BRANDING_ENABLED:
        return None
    admin_id = getattr(user, "assigned_admin_id", None)
    if not admin_id:
        return None
    admin = await User.get(admin_id)
    if (
        admin is None
        or admin.role != UserRole.ADMIN
        or admin.status != UserStatus.ACTIVE
        or not admin.custom_domain
        or admin.custom_domain_status != STATUS_READY
    ):
        return None
    return admin.custom_domain


async def all_active_custom_domains() -> list[str]:
    """Used by the dynamic CORS allow-list. Returns lowercase apex
    domains for every admin currently in READY status. Cheap query —
    sparse-unique index makes this an O(k) scan where k = number of
    admins with a domain set (≤ 100 expected)."""
    if not settings.BRANDING_ENABLED:
        return []
    coll = User.get_motor_collection()
    cursor = coll.find(
        {
            "custom_domain": {"$ne": None},
            "custom_domain_status": STATUS_READY,
            "role": UserRole.ADMIN.value,
            "status": UserStatus.ACTIVE.value,
        },
        {"custom_domain": 1},
    )
    return [doc["custom_domain"] async for doc in cursor]


# ── Resolve admin from a register request (host + referral) ──────────
async def resolve_signup_attribution(
    *,
    request_host: str | None,
    referral_code: str | None,
) -> tuple[PydanticObjectId | None, PydanticObjectId | None, list, str]:
    """Return ``(assigned_admin_id, assigned_broker_id, broker_ancestry, signup_origin)``
    for a /register call.

    Resolution order — first hit wins:
      1. If ``referral_code`` resolves to an active BROKER →
         BRANDED_REFERRAL with broker assignment (assigned_broker_id set,
         assigned_admin_id cascaded from broker's admin). Checked FIRST —
         a broker's link lands on the parent admin's custom domain, so it
         must beat the custom-domain match below.
      2. Else if the request hostname matches an admin's ``custom_domain``
         (and BRANDING_ENABLED) → CUSTOM_DOMAIN attribution.
      3. Else if ``referral_code`` resolves to an active ADMIN →
         BRANDED_REFERRAL (no broker assignment).
      4. Else → (None, None, [], PLATFORM) — super-admin pool.

    Always returns a 4-tuple even when branding is disabled so the
    register handler stays branchless.
    """
    # Broker referral is the MOST SPECIFIC signal and MUST win even on a
    # custom domain. A broker's registration link is
    # ``https://<parent-admin-domain>/register?ref=<broker_code>`` — the
    # request therefore lands on the ADMIN's custom domain. Resolving the
    # domain first (below) matched the admin and silently dropped the broker
    # attribution, so link-referred users landed straight in the admin's
    # pool (assigned_broker_id / broker_ancestry both null) and had to be
    # transferred to the broker by hand — and never showed on the broker's
    # dashboard (scoped by ``broker_ancestry``). Check the broker ref first.
    if referral_code:
        try:
            broker = await find_broker_by_user_code(referral_code)
        except Exception:  # pragma: no cover
            logger.exception(
                "branding_resolve_broker_by_user_code_failed code=%s", referral_code
            )
            broker = None
        if broker is not None:
            ancestry = list(broker.broker_ancestry or []) + [broker.id]
            return broker.assigned_admin_id, broker.id, ancestry, ORIGIN_BRANDED_REFERRAL

    # Custom domain attribution — requires BRANDING_ENABLED (white-label feature).
    if settings.BRANDING_ENABLED and request_host:
        try:
            admin = await find_admin_by_domain(request_host)
        except Exception:  # pragma: no cover - defensive
            logger.exception("branding_resolve_by_domain_failed host=%s", request_host)
            admin = None
        if admin is not None:
            return admin.id, None, [], ORIGIN_CUSTOM_DOMAIN

    # Admin referral code — fallback for platform-host signups carrying
    # ?ref=<admin_code> (no custom domain matched above). NOT gated by
    # BRANDING_ENABLED: core hierarchy logic, works regardless of the flag.
    if referral_code:
        try:
            admin = await find_admin_by_user_code(referral_code)
        except Exception:  # pragma: no cover
            logger.exception(
                "branding_resolve_by_user_code_failed code=%s", referral_code
            )
            admin = None
        if admin is not None:
            return admin.id, None, [], ORIGIN_BRANDED_REFERRAL

    return None, None, [], ORIGIN_PLATFORM


# ── Admin-side mutations ──────────────────────────────────────────────
async def update_branding(
    *,
    admin: User,
    brand_name: str | None = None,
    telegram_link: str | None = None,
    custom_domain: str | None = None,
    clear_custom_domain: bool = False,
) -> User:
    """Update brand_name and/or custom_domain on an ADMIN user.

    Setting ``custom_domain`` to a new value flips status to
    ``PENDING_DNS`` and clears any prior cert error, so the verify
    flow restarts cleanly. Pass ``clear_custom_domain=True`` to
    disconnect (status, error and verified_at are also cleared so
    the row looks pristine — the cert on disk is left alone).
    """
    _ensure_enabled()
    if admin.role != UserRole.ADMIN:
        raise ValidationFailedError("Branding is only available for ADMIN users")

    if brand_name is not None:
        # Empty string clears the brand name (frontend falls back to
        # the platform default), which is a deliberate user action.
        admin.brand_name = brand_name.strip() or None

    if telegram_link is not None:
        # Only accept a real https Telegram/http(s) URL so a stored value
        # can never inject a javascript: href on the public login page.
        # Empty string clears it (nothing shown).
        _tl = telegram_link.strip()
        if not _tl:
            admin.telegram_link = None
        elif _tl.lower().startswith(("https://", "http://")):
            admin.telegram_link = _tl[:300]
        else:
            raise ValidationFailedError(
                "Telegram link must start with https:// (e.g. https://t.me/yourchannel)"
            )

    if clear_custom_domain:
        admin.custom_domain = None
        admin.custom_domain_status = None
        admin.custom_domain_last_error = None
        admin.custom_domain_verified_at = None
    elif custom_domain is not None:
        norm = normalize_domain(custom_domain)
        if norm and norm != admin.custom_domain:
            # Uniqueness is enforced by the sparse-unique Mongo index
            # too (race-safe), but we check here for a clean 409.
            existing = await User.find_one(
                {"custom_domain": norm, "_id": {"$ne": admin.id}}
            )
            if existing is not None:
                raise ConflictError(
                    f"Domain '{norm}' is already connected to another admin",
                    details={"field": "custom_domain"},
                )
            admin.custom_domain = norm
            admin.custom_domain_status = STATUS_PENDING_DNS
            admin.custom_domain_last_error = None
            admin.custom_domain_verified_at = None

    await admin.save()
    return admin


async def save_logo(admin: User, *, content: bytes, mime: str) -> User:
    """Persist an uploaded logo to disk and update ``logo_url``.

    File is named ``logo-<admin_id>-<unix_ms>.<ext>`` so a refresh
    busts the CDN/browser cache automatically. Old logo (if any) is
    best-effort deleted to keep the dir from growing unbounded.
    """
    _ensure_enabled()
    if admin.role != UserRole.ADMIN:
        raise ValidationFailedError("Branding is only available for ADMIN users")
    if mime not in ALLOWED_LOGO_MIMES:
        raise ValidationFailedError(
            f"Unsupported logo mime '{mime}'. Allowed: "
            + ", ".join(sorted(ALLOWED_LOGO_MIMES))
        )
    if len(content) == 0:
        raise ValidationFailedError("Logo file is empty")
    if len(content) > MAX_LOGO_BYTES:
        raise ValidationFailedError(
            f"Logo too large ({len(content)} bytes). Max {MAX_LOGO_BYTES} bytes."
        )

    ext = ALLOWED_LOGO_EXTS[mime]
    ts_ms = int(now_utc().timestamp() * 1000)
    filename = f"logo-{admin.id}-{ts_ms}{ext}"
    path = LOGO_DIR / filename
    path.write_bytes(content)

    # Best-effort delete old file (different name → never collides).
    if admin.logo_url:
        try:
            old_name = Path(admin.logo_url).name
            old_path = LOGO_DIR / old_name
            if old_path.exists() and old_path != path:
                old_path.unlink()
        except Exception:  # pragma: no cover
            logger.exception("branding_old_logo_unlink_failed url=%s", admin.logo_url)

    admin.logo_url = f"/uploads/logos/{filename}"
    await admin.save()
    return admin


# ── DNS + SSL provisioning ────────────────────────────────────────────
# Strong references to in-flight provisioning tasks. asyncio keeps only
# weak references to tasks, so without this a certbot run can be
# collected mid-flight and simply vanish.
_PROVISION_TASKS: set = set()


def admin_host_for(domain: str) -> str:
    """The hostname the ADMIN panel is served on for a tenant domain.

    `admin.<domain>`, mirroring how the platform itself is laid out
    (admin.sachchasauda.com). Kept in one place because the DNS check,
    the preview, the provisioning helper, the CORS allow-list and the
    UI all have to agree on it.
    """
    return f"admin.{(domain or '').strip().lower().lstrip('.')}"


# Public recursive resolvers, used only as a fallback.
_PUBLIC_RESOLVERS: Final[list[str]] = ["8.8.8.8", "1.1.1.1", "8.8.4.4", "1.0.0.1"]


def _make_resolver(nameservers: list[str]):
    """A dnspython resolver that ignores the system config and our own
    negative cache, so a stale NXDOMAIN can't bite a retry."""
    import dns.resolver  # type: ignore

    r = dns.resolver.Resolver(configure=False)
    r.nameservers = nameservers
    r.lifetime = 5.0
    r.timeout = 5.0
    r.cache = None
    return r


def _authoritative_nameserver_ips(domain: str) -> list[str]:
    """IPs of the nameservers that are AUTHORITATIVE for ``domain``.

    We ask them directly instead of trusting a recursive resolver,
    because this host's UDP:53 is intercepted by the provider — a
    `dig @8.8.8.8` from the server returns the provider's own cached
    answer, not Google's. That is how a domain whose A record had
    already been corrected kept failing verification for an hour:
    every public resolver on the internet saw the new IP, and this one
    box saw the old one.

    Asking the authoritative servers is also the question we actually
    mean: "has the operator published this record", not "has some
    cache caught up yet".
    """
    import dns.exception  # type: ignore

    probe = _make_resolver(_PUBLIC_RESOLVERS)
    labels = (domain or "").strip(".").split(".")
    # Walk up: admin.foo.co.uk -> foo.co.uk -> co.uk, stopping at the
    # first zone that answers with NS records.
    for i in range(len(labels) - 1):
        zone = ".".join(labels[i:])
        try:
            ns_names = [str(r.target).rstrip(".") for r in probe.resolve(zone, "NS")]
        except dns.exception.DNSException:
            continue
        ips: list[str] = []
        for name in ns_names:
            try:
                ips.extend(rd.address for rd in probe.resolve(name, "A"))
            except dns.exception.DNSException:
                continue
        if ips:
            return ips
    return []


def _resolve_a_records(host: str, nameserver_ips: list[str]) -> tuple[set[str], str | None]:
    """``(ips, error_class_name_or_None)`` for one host."""
    import dns.exception  # type: ignore

    try:
        answers = _make_resolver(nameserver_ips).resolve(host, "A")
        return {rd.address for rd in answers}, None
    except dns.exception.DNSException as exc:
        return set(), exc.__class__.__name__


async def check_dns_a_record(domain: str) -> tuple[bool, str | None]:
    """Resolve A records for both apex + www and confirm at least one
    points at ``settings.PLATFORM_PUBLIC_IP``.

    Returns ``(ok, error_message_or_None)``. Designed to be called
    from the verify endpoint *before* enqueuing certbot — bad DNS
    means certbot would fail anyway, and we'd waste a Let's Encrypt
    rate-limit slot.
    """
    target_ip = (settings.PLATFORM_PUBLIC_IP or "").strip()
    if not target_ip:
        return False, (
            "PLATFORM_PUBLIC_IP is not configured on the server; "
            "cannot verify DNS until the operator sets it."
        )

    try:
        import dns.resolver  # type: ignore  # noqa: F401 - availability probe
    except ImportError:
        return False, (
            "dnspython is not installed in the backend env; "
            "run `pip install dnspython` and redeploy."
        )

    apex_ok = False
    www_ok = False
    seen: list[str] = []

    # Bypass the system resolver (e.g. systemd-resolved, dnsmasq) and
    # query Google + Cloudflare directly. Two reasons:
    #   1. The system resolver aggressively caches NXDOMAIN. If an admin
    #      added their A records minutes after we first checked, the
    #      negative cache (typically 15s–1h) keeps returning NXDOMAIN
    #      until it expires — manifesting as the bug where `dig` from
    #      the same host shows the right IP but our verify endpoint
    #      keeps failing.
    #   2. Public resolvers see the latest authoritative answer fastest
    #      and have no per-tenant negative cache that can wedge us.
    # Authoritative first, public resolvers only if that fails — see
    # `_authoritative_nameserver_ips` for why a recursive answer can't
    # be trusted from this host.
    nameservers = _authoritative_nameserver_ips(domain) or _PUBLIC_RESOLVERS

    # The admin host is checked too, but it is OPTIONAL: a tenant who
    # only wants the trading app keeps working exactly as before, and
    # certbot is simply not asked for a name that doesn't resolve —
    # asking would fail the whole certificate, not just that name.
    admin_ok = False
    for host, target_flag in (
        (domain, "apex"),
        (f"www.{domain}", "www"),
        (admin_host_for(domain), "admin"),
    ):
        ips, err = _resolve_a_records(host, nameservers)
        if err:
            seen.append(f"{host}=ERR({err})")
            continue
        seen.append(f"{host}={','.join(sorted(ips)) or 'none'}")
        if target_ip in ips:
            if target_flag == "apex":
                apex_ok = True
            elif target_flag == "www":
                www_ok = True
            else:
                admin_ok = True

    # Apex MUST resolve to us (it's the canonical record). www is
    # nice-to-have — if it doesn't, we let certbot fail naturally on
    # that name and surface the error.
    if not apex_ok:
        return False, (
            f"A record for {domain} does not point to {target_ip}. "
            f"Found: {'; '.join(seen)}"
        )
    _LAST_ADMIN_DNS[domain] = admin_ok
    return True, None


# Whether `admin.<domain>` resolved to us on the last check, so the
# provisioning step knows whether to ask certbot for that name.
_LAST_ADMIN_DNS: dict[str, bool] = {}


async def admin_host_resolves(domain: str) -> bool:
    """Does `admin.<domain>` point at us? Re-checked rather than trusted
    from the cache above when provisioning runs in a separate process."""
    ok, _ = await check_dns_a_record(domain)
    if not ok:
        return False
    return _LAST_ADMIN_DNS.get(domain, False)


async def resolve_dns_preview(domain: str) -> dict:
    """Return a side-by-side preview of the apex + www A records vs the
    expected ``PLATFORM_PUBLIC_IP``. Used by the admin UI to show the
    current registrar values right next to "Update to" so the admin can
    confidently spot exactly which records need editing.

    Shape (always returns this shape, even on errors):
    ::
        {
            "expected_ip": "82.25.110.52",
            "apex": {"current": ["84.32.84.32"], "ok": False, "error": None},
            "www":  {"current": [],              "ok": False, "error": "NXDOMAIN"},
            "admin":{"current": [],              "ok": False, "error": "NXDOMAIN"},
        }

    The ``admin`` row is the admin panel's own host and is OPTIONAL —
    a tenant who skips it keeps a working trading app.

    Where ``ok`` means at least one resolved A record matches
    ``expected_ip``. Errors are returned per-host (NXDOMAIN, timeout)
    so the UI can render them inline without a 500.
    """
    expected_ip = (settings.PLATFORM_PUBLIC_IP or "").strip()
    out: dict = {
        "expected_ip": expected_ip or None,
        "apex": {"current": [], "ok": False, "error": None},
        "www": {"current": [], "ok": False, "error": None},
        "admin": {"current": [], "ok": False, "error": None},
    }
    if not expected_ip:
        out["apex"]["error"] = "PLATFORM_PUBLIC_IP not configured on server"
        out["www"]["error"] = out["apex"]["error"]
        out["admin"]["error"] = out["apex"]["error"]
        return out

    norm = normalize_domain(domain)
    if not norm:
        out["apex"]["error"] = "Invalid domain"
        out["www"]["error"] = "Invalid domain"
        out["admin"]["error"] = "Invalid domain"
        return out

    try:
        import dns.resolver  # type: ignore  # noqa: F401 - availability probe
    except ImportError:
        out["apex"]["error"] = "dnspython not installed in backend"
        out["www"]["error"] = out["apex"]["error"]
        out["admin"]["error"] = out["apex"]["error"]
        return out

    # Authoritative, same as check_dns_a_record — the table the admin
    # reads has to agree with the check that gates provisioning, or
    # they see green rows next to a failure.
    nameservers = _authoritative_nameserver_ips(norm) or _PUBLIC_RESOLVERS

    for host, key in (
        (norm, "apex"),
        (f"www.{norm}", "www"),
        (admin_host_for(norm), "admin"),
    ):
        ips, err = _resolve_a_records(host, nameservers)
        if err:
            out[key]["error"] = err
            continue
        out[key]["current"] = sorted(ips)
        out[key]["ok"] = expected_ip in ips
    return out


async def begin_domain_verification(admin: User) -> User:
    """Trigger DNS check + enqueue cert-provisioning Celery task.

    Mutates the admin's status fields synchronously so the UI poll
    sees progress within the same tick. The actual ``certbot`` call
    happens on a worker (see ``app.workers.branding_tasks``).
    """
    _ensure_enabled()
    if admin.role != UserRole.ADMIN:
        raise ValidationFailedError("Branding is only available for ADMIN users")
    if not admin.custom_domain:
        raise ValidationFailedError(
            "No custom_domain set. Save a domain first via PUT /admin/branding."
        )

    ok, err = await check_dns_a_record(admin.custom_domain)
    if not ok:
        admin.custom_domain_status = STATUS_FAILED
        admin.custom_domain_last_error = err or "DNS check failed"
        await admin.save()
        return admin

    admin.custom_domain_status = STATUS_PROVISIONING
    admin.custom_domain_last_error = None
    await admin.save()

    # Run it on THIS process, in the background. It used to be
    # `provision_ssl.delay(...)`, but this is the only Celery task in
    # the codebase and no worker has ever run in production — the job
    # went into Redis and stayed there, so the UI sat on
    # "Provisioning…" forever with nothing to show for it. Standing up
    # a worker to carry one occasional job is more moving parts than
    # the job is worth; certbot already runs in a thread.
    #
    # Imported lazily so boot ordering (workers → models → services →
    # workers) stays acyclic.
    try:
        from app.workers.branding_tasks import run_provisioning

        admin_id = str(admin.id)

        async def _provision() -> None:
            try:
                await run_provisioning(admin_id)
            except Exception:  # pragma: no cover - never kill the loop
                logger.exception("branding_provision_ssl_crashed admin_id=%s", admin_id)
                with contextlib.suppress(Exception):
                    await mark_domain_failed(
                        admin.id, "Provisioning crashed — see server logs."
                    )

        # Held on the app so the garbage collector can't drop a running
        # task mid-certbot; discarded as soon as it finishes.
        task = asyncio.create_task(_provision())
        _PROVISION_TASKS.add(task)
        task.add_done_callback(_PROVISION_TASKS.discard)
    except Exception:  # pragma: no cover
        logger.exception("branding_provision_ssl_start_failed admin_id=%s", admin.id)
        admin.custom_domain_status = STATUS_FAILED
        admin.custom_domain_last_error = (
            "Could not start SSL provisioning. Check the server logs."
        )
        await admin.save()
    return admin


async def disconnect_domain(admin: User) -> User:
    """Clear ``custom_domain`` + status. Cert on disk is left alone
    (harmless until expiry) so re-connecting later is fast."""
    _ensure_enabled()
    if admin.role != UserRole.ADMIN:
        raise ValidationFailedError("Branding is only available for ADMIN users")
    admin.custom_domain = None
    admin.custom_domain_status = None
    admin.custom_domain_last_error = None
    admin.custom_domain_verified_at = None
    await admin.save()
    return admin


# ── Status mutators (used by the Celery worker) ──────────────────────
async def mark_domain_ready(admin_id: PydanticObjectId | str) -> None:
    user = await User.get(PydanticObjectId(str(admin_id)))
    if user is None:
        return
    user.custom_domain_status = STATUS_READY
    user.custom_domain_last_error = None
    user.custom_domain_verified_at = now_utc()
    await user.save()


async def mark_domain_failed(
    admin_id: PydanticObjectId | str, error: str
) -> None:
    user = await User.get(PydanticObjectId(str(admin_id)))
    if user is None:
        return
    user.custom_domain_status = STATUS_FAILED
    user.custom_domain_last_error = (error or "")[:500]
    user.custom_domain_verified_at = now_utc()
    await user.save()
