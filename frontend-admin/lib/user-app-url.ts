"use client";

/**
 * Where a client-facing link an admin or broker shares must point.
 *
 * These links (referral / signup / login / download) are for END USERS, so
 * they have to land on the trading app — never on the admin panel host this
 * code is running in. Three pages used to carry their own copy of this
 * resolution and they had drifted: the dashboard's referral link fell back
 * to a hardcoded `https://app.sachchasauda.com`, a host that is not the
 * user app, while the Branding and Download-App pages correctly derived
 * the apex from the current origin.
 *
 * Resolution order, most specific first:
 *
 *   1. The actor's OWN connected domain, once SSL is live
 *      (`custom_domain_status === "READY"`). For a BROKER the backend
 *      resolves the PARENT ADMIN's domain into the same two fields
 *      (`_branding_fields_for`), so a Rising Bull broker gets
 *      `risingbull.live` without the frontend walking any hierarchy.
 *   2. `NEXT_PUBLIC_USER_APP_URL` — explicit deploy-time override.
 *   3. The current panel origin minus its `admin.` prefix. This is what
 *      makes an un-configured deploy behave: a panel served from
 *      `admin.sachchasauda.com` hands out `sachchasauda.com`, and one on
 *      `admin.risingbull.live` hands out `risingbull.live`.
 *   4. `https://sachchasauda.com` — SSR and mis-config backstop.
 */

export type BrandedActor =
  | {
      custom_domain?: string | null;
      custom_domain_status?: string | null;
    }
  | null
  | undefined;

const PLATFORM_FALLBACK = "https://sachchasauda.com";

/** Trailing slash off; http upgraded to https except on a dev host, where
 *  the user app really is served over plain http. */
function normalize(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, "");
  return /^http:\/\/(localhost|127\.0\.0\.1)(:|$)/.test(trimmed)
    ? trimmed
    : trimmed.replace(/^http:/, "https:");
}

/** The PLATFORM's end-user app origin — steps 2 → 4 above. Use this for
 *  links that are deliberately platform-hosted and carry `?ref=`. */
export function platformUserAppOrigin(): string {
  const fromEnv = process.env.NEXT_PUBLIC_USER_APP_URL || "";
  if (fromEnv.trim()) return normalize(fromEnv);
  if (typeof window === "undefined") return PLATFORM_FALLBACK;
  try {
    const url = new URL(window.location.origin);
    if (url.hostname.startsWith("admin.")) {
      url.hostname = url.hostname.slice("admin.".length);
    }
    return normalize(url.origin);
  } catch {
    return PLATFORM_FALLBACK;
  }
}

/** The origin THIS actor's client-facing links should use — their own
 *  white-labelled domain when one is live, else the platform's. */
export function userAppOrigin(actor: BrandedActor): string {
  const domain = tenantDomain(actor);
  return domain ? `https://${domain}` : platformUserAppOrigin();
}

/**
 * The ADMIN-panel origin for links this actor hands to their own staff —
 * the employee-login link, specifically.
 *
 * The panel rides on `admin.<domain>`, so a white-labelled admin's
 * employees sign in at `admin.risingbull.live`, not on the platform host
 * the admin happens to be using right now. Falls back to the current
 * origin, which IS an admin host, so an un-branded admin keeps today's
 * behaviour exactly.
 */
export function adminPanelOrigin(actor: BrandedActor): string {
  const domain = tenantDomain(actor);
  if (domain) return `https://admin.${domain}`;
  if (typeof window !== "undefined") return normalize(window.location.origin);
  return "https://admin.sachchasauda.com";
}

/** The actor's own domain, bare, only once SSL is live. */
function tenantDomain(actor: BrandedActor): string | null {
  const domain = (actor?.custom_domain || "").trim();
  if (!domain || actor?.custom_domain_status !== "READY") return null;
  return domain.replace(/^https?:\/\//, "").replace(/\/+$/, "");
}
