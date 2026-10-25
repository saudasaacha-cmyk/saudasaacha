"use client";

import { useEffect, useRef } from "react";
import { useAdminAuthStore } from "@/stores/authStore";
import { useHostBranding } from "@/lib/useHostBranding";
import { API_URL, APP_NAME } from "@/lib/constants";

// Applies tenant white-label chrome (browser tab title + favicon) on
// the admin panel for every tenant-side role (ADMIN / BROKER /
// EMPLOYEE) whose authStore carries `brand_name` / `logo_url`.
// Super-admins always see the platform default. The favicon swap
// rewrites every existing <link rel="icon"> the SSR HTML shipped with —
// appending a new node alone doesn't visibly change the tab icon
// because the browser has already committed the SSR-supplied icon. We stash the original href
// once on a data-attribute so that signing out / SUPER_ADMIN sessions
// cleanly restore the platform sprout.
//
// Mounted inside `<Providers>` so it lives for the whole admin app.
export function AdminBrandingChrome() {
  const admin = useAdminAuthStore((s) => s.admin);
  // The HOST is the fallback source, and the only one available before
  // sign-in: on admin.<tenant-domain> the login screen had no admin to
  // read a brand from, so the tab said "RIZING BULL Admin" to
  // people who have never heard of the platform.
  const hostBrand = useHostBranding();
  const role = admin?.role;
  const userCode = (admin?.user_code ?? "").trim();
  // For a BROKER or EMPLOYEE this is their EMPLOYER's domain — the
  // backend resolves it through the same parent hop as the brand name.
  const tenantDomain = (admin?.custom_domain ?? "").trim().toLowerCase();

  // SUPER_ADMIN never gets tenant chrome — always platform default, even
  // when they are working on a tenant's host.
  const isTenant = role === "ADMIN" || role === "BROKER" || role === "EMPLOYEE";
  const isSuper = role === "SUPER_ADMIN";
  // Signed-in brand wins over the host's; the host covers pre-login.
  // EMPLOYEE belongs in `isTenant` because the backend resolves their
  // employer's brand into these same payload fields — while it didn't,
  // an employee of a white-labelled admin read "ACME" in the sidebar
  // and the platform's name in the tab, favicon and installed app.
  const brandName = (
    (isTenant ? admin?.brand_name : null) ??
    (isSuper ? null : hostBrand.brand_name) ??
    ""
  ).trim();
  const logoPath =
    (isTenant ? admin?.logo_url : null) ??
    (isSuper ? null : hostBrand.logo_url) ??
    null;

  const tenantName = brandName || null;
  const tenantLogo = logoPath
    ? logoPath.startsWith("http")
      ? logoPath
      : `${API_URL}${logoPath}`
    : null;
  // Whether this component has ever written a tenant title — see the
  // title block below for why it matters.
  const appliedTenantTitle = useRef(false);

  useEffect(() => {
    if (typeof document === "undefined") return;

    // ── Title ───────────────────────────────────────────────────────
    // Only ever WRITE a tenant name. The platform default is already in
    // the server-rendered <title>, and this effect runs before the host
    // fetch resolves — writing APP_NAME here would stomp the correct
    // title the auth layout just rendered on a tenant host, producing
    // the very flash this is meant to remove. The platform name is
    // restored only when we had previously applied a tenant one (sign
    // out, or a super admin taking over the tab).
    if (tenantName) {
      appliedTenantTitle.current = true;
      if (document.title !== tenantName) document.title = tenantName;
    } else if (appliedTenantTitle.current) {
      appliedTenantTitle.current = false;
      if (document.title !== APP_NAME) document.title = APP_NAME;
    }

    // ── Favicon ────────────────────────────────────────────────────
    const head = document.head;
    if (!head) return;
    const icons = head.querySelectorAll<HTMLLinkElement>(
      'link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]',
    );
    // CRITICAL: mutate href in place — DO NOT clone+replaceWith.
    // Next.js renders these <link> nodes through React's metadata
    // system; removing them out-of-tree leaves the reconciler with
    // dangling refs and crashes the next navigation with
    //   "Cannot read properties of null (reading 'removeChild')".
    icons.forEach((el) => {
      if (!el.dataset.brandingOriginal) {
        el.dataset.brandingOriginal = el.getAttribute("href") || "";
      }
      if (tenantLogo) {
        if (el.getAttribute("href") !== tenantLogo) {
          el.setAttribute("href", tenantLogo);
        }
        el.setAttribute("data-branding", "1");
      } else {
        const original = el.dataset.brandingOriginal || "";
        if (original && el.getAttribute("href") !== original) {
          el.setAttribute("href", original);
        }
        el.removeAttribute("data-branding");
      }
    });
    // Append a SINGLE branding-owned <link> at the end of <head> so
    // browsers (which honour the LAST applicable icon) update the tab
    // immediately. This node is outside the React tree and safe to
    // mutate / remove without breaking reconciliation.
    const OWN_ID = "branding-favicon-runtime";
    const existing = head.querySelector<HTMLLinkElement>(`link#${OWN_ID}`);
    if (tenantLogo) {
      if (existing) {
        if (existing.getAttribute("href") !== tenantLogo) {
          existing.setAttribute("href", tenantLogo);
        }
      } else {
        const link = document.createElement("link");
        link.id = OWN_ID;
        link.rel = "icon";
        link.href = tenantLogo;
        if (tenantLogo.endsWith(".svg")) link.type = "image/svg+xml";
        else if (tenantLogo.endsWith(".png")) link.type = "image/png";
        else if (tenantLogo.endsWith(".webp")) link.type = "image/webp";
        else if (tenantLogo.endsWith(".jpg") || tenantLogo.endsWith(".jpeg"))
          link.type = "image/jpeg";
        head.appendChild(link);
      }
    } else if (existing) {
      existing.remove();
    }

    // ── PWA manifest ───────────────────────────────────────────────
    // Point the <link rel="manifest"> at the per-tenant URL so when the
    // admin clicks "Install app" the OS launcher picks up THEIR brand
    // name + logo. Super-admins / pre-login keep the platform default.
    const manifestEl = head.querySelector<HTMLLinkElement>('link[rel="manifest"]');
    if (manifestEl) {
      // `?u=` once we know who is signed in; `?d=` on a tenant host
      // before that, so an install from the login screen is still named
      // and iconed for the tenant rather than "RB Admin".
      const host = window.location.hostname.toLowerCase();
      // `?u=` keys off `/branding/by-code`, which resolves ADMIN rows
      // only — a broker's or employee's own code 404s there.
      //
      // For them the auth payload already carries their EMPLOYER's
      // `custom_domain`, so `?d=` works on any host, including the
      // platform's own. Without this a broker or employee signing in at
      // admin.rizingbull.in installed a home-screen app named for the
      // platform while their sidebar, tab and favicon all said the
      // tenant — the one surface that stayed wrong after the rest was
      // fixed. Falls through to the browser's host only when the payload
      // has no domain (an admin who never connected one).
      const brandedHost =
        tenantDomain || (hostBrand.brand_name || hostBrand.logo_url ? host : "");
      const desired =
        role === "ADMIN" && userCode
          ? `/manifest.webmanifest?u=${encodeURIComponent(userCode)}`
          : !isSuper && brandedHost
            ? `/manifest.webmanifest?d=${encodeURIComponent(brandedHost)}`
            : "/manifest.webmanifest";
      if (manifestEl.getAttribute("href") !== desired) {
        manifestEl.setAttribute("href", desired);
      }
    }

    // iOS home-screen label. Static in the SSR <head>, so it needs the
    // same runtime swap as the title for a tenant install to read right.
    const appleTitle = head.querySelector<HTMLMetaElement>(
      'meta[name="apple-mobile-web-app-title"]',
    );
    if (appleTitle) {
      const desired = tenantName || "RB Admin";
      if (appleTitle.getAttribute("content") !== desired) {
        appleTitle.setAttribute("content", desired);
      }
    }
  }, [
    tenantName,
    tenantLogo,
    role,
    isSuper,
    userCode,
    tenantDomain,
    hostBrand.brand_name,
    hostBrand.logo_url,
  ]);

  return null;
}
