"use client";

import Link from "next/link";
import { MpContainer } from "./mp-ui";
import { useBranding } from "@/lib/branding-context";
import { API_URL } from "@/lib/constants";

// Broker sitemap — Trading markets, Platforms, Company and Support/Legal.
const COLS: { title: string; links: { href: string; label: string }[] }[] = [
  {
    title: "Trading",
    links: [
      { href: "/equity", label: "Equity" },
      { href: "/futures-options", label: "Futures & Options" },
      { href: "/commodities", label: "Commodities" },
      { href: "/indices", label: "Indices" },
    ],
  },
  {
    title: "Platform",
    links: [
      { href: "/web-terminal", label: "Web Terminal" },
      { href: "/pro", label: "Pro Account" },
      { href: "/demo", label: "Paper Trading" },
      { href: "/pricing", label: "Pricing" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About" },
      { href: "/blog", label: "Blog" },
      { href: "/education", label: "Education" },
      { href: "/contact", label: "Contact" },
    ],
  },
  {
    title: "Support & Legal",
    links: [
      { href: "/how-it-works", label: "How it works" },
      { href: "/faq", label: "FAQ" },
      { href: "/legal/refund", label: "Refund Policy" },
      { href: "/legal/terms", label: "Terms & Conditions" },
      { href: "/privacy", label: "Privacy Policy" },
    ],
  },
];

export function MarketingFooter() {
  const year = new Date().getFullYear();
  const { branding, showPlatformDefault } = useBranding();
  const brandName = (branding?.brand_name ?? "").trim();
  const logoSrc = branding?.logo_url ? `${API_URL}${branding.logo_url}` : null;
  // On a tenant's branded domain, never reveal "SaudaSaacha". Show the
  // tenant's own name/logo when resolved, else a neutral placeholder.
  const displayName = brandName || (showPlatformDefault ? "SaudaSaacha" : "");

  return (
    <footer className="mp-dark border-t border-mp-border bg-mp-bg text-mp-text">
      <MpContainer className="py-14 sm:py-16">
        <div className="grid grid-cols-2 gap-10 lg:grid-cols-6">
          {/* Brand block — footer sits inside an `.mp-dark` scope, so use the
              light brand mark (white wordmark) for contrast. */}
          <div className="col-span-2">
            <Link href="/" className="inline-flex items-center gap-2.5">
              {logoSrc ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={logoSrc}
                    alt={brandName || "Logo"}
                    className="h-14 w-auto rounded object-contain"
                  />
                  {brandName && (
                    <span className="font-display text-xl font-bold tracking-tight text-mp-text">
                      {brandName}
                    </span>
                  )}
                </>
              ) : showPlatformDefault ? (
                // Platform host only — the super-admin SaudaSaacha lockup.
                <Wordmark className="text-mp-text" markClassName="size-12" textClassName="text-3xl" />
              ) : (
                // Branded domain / brand unresolved — nothing, never SaudaSaacha.
                <span className="font-display text-xl font-bold tracking-tight text-mp-text">
                  {displayName}
                </span>
              )}
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-mp-text-mut">
              A SEBI-registered stock broker built in India. Trade Equity, F&O,
              Commodities, IPOs and Mutual Funds across NSE, BSE & MCX from a
              single account.
            </p>
          </div>

          {/* Link columns */}
          {COLS.map((col) => (
            <div key={col.title}>
              <div className="text-sm font-semibold text-mp-text">
                {col.title}
              </div>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.href + l.label}>
                    <Link
                      href={l.href}
                      className="text-sm text-mp-text-mut transition-colors hover:text-mp-text"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Compliance disclaimer (fixed copy) */}
        <div className="mt-12 border-t border-mp-border pt-8">
          <p className="max-w-4xl text-[12px] leading-relaxed text-mp-text-mut">
            {displayName || "This platform"} is a SEBI-registered stock broker
            offering trading and investing across NSE, BSE & MCX. Investments in
            the securities market
            are subject to market risks; read all the related documents carefully
            before investing. Nothing on this site is investment advice or a
            solicitation to trade, and past performance does not guarantee future
            results. Trade only with money you can afford to lose.
          </p>
          <p className="mt-4 text-[12px] text-mp-text-mut">
            © {year} {displayName || "This platform"}. All rights reserved.
          </p>
        </div>
      </MpContainer>
    </footer>
  );
}
