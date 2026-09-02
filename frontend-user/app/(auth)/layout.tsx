"use client";

import { Suspense, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import { BrandGlyph } from "@/components/layout/BrandGlyph";
import { Wordmark } from "@/components/layout/Wordmark";
import { useBranding } from "@/lib/branding-context";
import { API_URL } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { SmokeyBackground } from "@/components/ui/smokey-background";

/**
 * Tenant brand tile — ALWAYS renders the brand glyph on the brand
 * gradient so something is visible no matter what.  When the admin
 * has uploaded a logo AND the image successfully loads, it's
 * rendered on top of the glyph (covers it).  If the image fails
 * to load or hasn't been configured, the user still sees the
 * original glyph-on-gradient look from before the logo feature
 * existed.  This guarantees zero blank tiles in production.
 */
function BrandTile({
  logoSrc,
  alt,
  size = "lg",
}: {
  logoSrc: string | null;
  alt: string;
  size?: "sm" | "lg";
}) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const sizeCls = size === "lg" ? "size-16" : "size-10";
  const iconCls = size === "lg" ? "size-8" : "size-5";
  return (
    <div
      className={cn(
        "relative grid place-items-center overflow-hidden rounded-2xl bg-foreground text-background shadow-lg shadow-foreground/20 ring-1 ring-foreground/10",
        sizeCls,
      )}
    >
      <BrandGlyph className={iconCls} />
      {logoSrc && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={logoSrc}
          alt={alt}
          onLoad={() => setImgLoaded(true)}
          onError={() => setImgLoaded(false)}
          className={cn(
            "absolute inset-0 rounded-2xl bg-card object-contain p-1 transition-opacity",
            imgLoaded ? "opacity-100" : "opacity-0",
          )}
        />
      )}
    </div>
  );
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={<main className="min-h-screen w-full bg-background" />}
    >
      <AuthLayoutInner>{children}</AuthLayoutInner>
    </Suspense>
  );
}

function AuthLayoutInner({ children }: { children: React.ReactNode }) {
  const searchParams = useSearchParams();
  const pathname = usePathname() || "";
  const { branding, showPlatformDefault } = useBranding();
  const tenantName = (branding?.brand_name ?? "").trim();
  // On a tenant's branded domain the super-admin "SaudaSaacha" name/logo must
  // never appear. Use it only on the confirmed platform host; elsewhere fall
  // back to empty / a neutral glyph until the tenant brand resolves.
  const platformName = showPlatformDefault ? "SaudaSaacha" : "";
  // Tenant logo uploaded by admin / super-admin via /settings/branding.
  // Mirrors BrandLogo.tsx: paths are server-relative, so prefix API_URL.
  // Falls back to the default brand glyph when no logo is configured.
  const logoSrc = branding?.logo_url
    ? `${API_URL}${branding.logo_url}`
    : null;

  const isImpersonating = !!(
    searchParams?.get("access") && searchParams?.get("refresh")
  );

  // Show the Login/Register tab bar only on those two routes; hide on
  // forgot-password / 2fa / impersonation handoff so those pages keep a
  // clean single-purpose layout.
  const showTabs = pathname === "/login" || pathname === "/register";
  const onRegister = pathname === "/register";

  if (isImpersonating) {
    return (
      <main className="grid min-h-screen w-full place-items-center bg-background">
        {children}
      </main>
    );
  }

  const tabs = showTabs ? (
    <div className="mb-6 inline-flex w-full rounded-xl bg-muted/40 p-1 ring-1 ring-inset ring-border/40">
      <Link
        href="/login"
        className={cn(
          "flex-1 rounded-lg px-3 py-2 text-center text-sm font-semibold transition-all",
          !onRegister
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        Login
      </Link>
      <Link
        href="/register"
        className={cn(
          "flex-1 rounded-lg px-3 py-2 text-center text-sm font-semibold transition-all",
          onRegister
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        Register
      </Link>
    </div>
  ) : null;

  const brandMark = (
    <Link href="/" className="mb-6 inline-flex items-center gap-2.5">
      {logoSrc ? (
        <>
          <BrandTile logoSrc={logoSrc} alt={tenantName || "Logo"} size="sm" />
          <span className="text-lg font-bold tracking-tight text-foreground">
            {tenantName || platformName}
          </span>
        </>
      ) : showPlatformDefault ? (
        // Platform host only — the super-admin's SaudaSaacha lockup.
        <Wordmark className="text-foreground" />
      ) : (
        // Branded domain (or brand not resolved yet) — neutral glyph tile,
        // NEVER the SaudaSaacha logo. The tenant logo replaces it once the
        // /branding/by-domain fetch (or its per-host cache) lands.
        <BrandTile logoSrc={null} alt="" size="sm" />
      )}
    </Link>
  );

  return (
    <main className="grid min-h-screen w-full place-items-center bg-gradient-to-br from-muted/40 via-background to-muted/40 p-4 sm:p-6">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-border/50 bg-card shadow-2xl shadow-primary/10 lg:grid-cols-2">
        {/* ── Left panel (desktop) — animated green smoke shader ──── */}
        <div className="relative hidden flex-col justify-end gap-8 overflow-hidden bg-[#06140d] p-10 text-white lg:flex">
          {/* Interactive WebGL smoke, brand-green */}
          <SmokeyBackground color="#16A34A" backdropBlurAmount="sm" />
          {/* Bottom fade so the tagline stays legible over the smoke */}
          <div
            className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent"
            aria-hidden
          />

          <div className="relative z-10">
            <p className="text-sm font-medium text-white/80">You can easily</p>
            <h2 className="mt-2 max-w-sm text-2xl font-bold leading-snug text-white xl:text-3xl">
              Trade Indian markets with clarity, speed and control.
            </h2>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/75">
              Equity, F&amp;O, Commodities, IPOs and Mutual Funds — all from one
              account on NSE, BSE &amp; MCX.
            </p>
          </div>

          <div className="relative z-10 text-xs text-white/60">
            &copy; {new Date().getFullYear()} {tenantName || platformName} · All
            rights reserved
          </div>
        </div>

        {/* ── Right form panel ───────────────────────────────────── */}
        <div className="relative bg-card p-6 sm:p-10">
          {brandMark}
          {tabs}
          {children}
        </div>
      </div>
    </main>
  );
}
