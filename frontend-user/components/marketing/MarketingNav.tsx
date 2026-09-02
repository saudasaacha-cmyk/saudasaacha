"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";
import { BrandGlyph } from "@/components/layout/BrandGlyph";
import { Wordmark } from "@/components/layout/Wordmark";
import { cn } from "@/lib/utils";
import { useBranding } from "@/lib/branding-context";
import { API_URL } from "@/lib/constants";

type NavLink = {
  href: string;
  label: string;
  children?: { href: string; label: string }[];
};

// Home points to "/"; the middle items scroll to the matching homepage
// section; About & Contact are their own pages. "Trading" has a dropdown
// that jumps to each market card.
const NAV_LINKS: NavLink[] = [
  { href: "/", label: "Home" },
  {
    href: "/#markets",
    label: "Trading",
    children: [
      { href: "/equity", label: "Equity" },
      { href: "/futures-options", label: "Futures & Options" },
      { href: "/commodities", label: "Commodities" },
      { href: "/indices", label: "Indices" },
    ],
  },
  {
    href: "/#platform",
    label: "Platforms",
    children: [
      { href: "/standard", label: "Standard" },
      { href: "/pro", label: "Pro" },
      { href: "/demo", label: "Demo" },
    ],
  },
  { href: "/#accounts", label: "Accounts" },
  { href: "/education", label: "Education" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function MarketingNav() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  // Which parent group is expanded in the mobile menu (accordion).
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const { branding, showPlatformDefault } = useBranding();
  const customName = (branding?.brand_name ?? "").trim();
  const logoSrc = branding?.logo_url ? `${API_URL}${branding.logo_url}` : null;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
    setOpenGroup(null);
  }, [pathname]);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname?.startsWith(href);

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-5 sm:pt-4">
      <div className="mx-auto max-w-mp-content">
        {/* White pill bar */}
        <div
          className={cn(
            "flex items-center gap-3 rounded-2xl bg-white px-3 py-2.5 ring-1 ring-gray-200 transition-shadow duration-300 sm:px-4",
            scrolled
              ? "shadow-lg shadow-black/10"
              : "shadow-md shadow-black/5",
          )}
        >
          {/* Logo */}
          <Link href="/" className="flex shrink-0 items-center gap-2.5">
            {logoSrc ? (
              <>
                <span className="grid size-9 place-items-center rounded-xl bg-mp-primary/10">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={logoSrc}
                    alt={customName || "Logo"}
                    className="size-6 rounded object-contain"
                  />
                </span>
                <span className="font-display text-lg font-bold tracking-tight text-black">
                  {customName || (showPlatformDefault ? "SaudaSaacha" : "")}
                </span>
              </>
            ) : showPlatformDefault ? (
              // Platform host only — the super-admin SaudaSaacha lockup.
              <Wordmark className="text-mp-text" />
            ) : (
              // Branded domain / brand unresolved — neutral glyph, no SaudaSaacha.
              <span className="grid size-9 place-items-center rounded-xl bg-mp-text/[0.06]">
                <BrandGlyph className="size-6 text-mp-text" />
              </span>
            )}
          </Link>

          {/* Desktop nav */}
          <nav className="mx-auto hidden items-center gap-0.5 lg:flex">
            {NAV_LINKS.map((l) => {
              const active = isActive(l.href);
              const base =
                "rounded-full px-3 py-2 text-[13px] font-medium transition-colors";
              const tone = active
                ? "bg-mp-primary/10 font-semibold text-mp-primary"
                : "text-black hover:bg-gray-100 hover:text-black";

              if (l.children) {
                return (
                  <div key={l.href} className="group relative">
                    <Link
                      href={l.href}
                      className={cn(base, tone, "inline-flex items-center gap-1")}
                    >
                      {l.label}
                      <ChevronDown className="size-3.5 transition-transform duration-200 group-hover:rotate-180" />
                    </Link>
                    {/* pt-2 bridges the gap so the panel stays open on hover */}
                    <div className="invisible absolute left-0 top-full pt-2 opacity-0 transition-all duration-150 group-hover:visible group-hover:opacity-100">
                      <div className="min-w-[210px] rounded-2xl bg-white p-2 shadow-lg shadow-black/10 ring-1 ring-gray-200">
                        {l.children.map((c) => (
                          <Link
                            key={c.label}
                            href={c.href}
                            className="block rounded-xl px-3 py-2 text-[13px] font-medium text-black transition-colors hover:bg-gray-100 hover:text-mp-primary"
                          >
                            {c.label}
                          </Link>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <Link key={l.href} href={l.href} className={cn(base, tone)}>
                  {l.label}
                </Link>
              );
            })}
          </nav>

          {/* Right cluster */}
          <div className="ml-auto flex items-center gap-2 lg:ml-0">
            <Link
              href="/login"
              className="hidden rounded-full px-3 py-2 text-sm font-medium text-black transition-colors hover:bg-gray-100 xl:block"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="hidden rounded-full bg-mp-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-mp-primary-2 lg:inline-flex"
            >
              Open Account
            </Link>

            {/* Mobile menu trigger */}
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              className="grid size-10 place-items-center rounded-xl bg-gray-100 text-black transition-colors hover:bg-gray-200 lg:hidden"
              aria-label={open ? "Close menu" : "Open menu"}
              aria-expanded={open}
            >
              {open ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {open && (
          <div className="mt-2 overflow-hidden rounded-2xl bg-white p-2 shadow-lg shadow-black/10 ring-1 ring-gray-200 lg:hidden">
            <nav className="flex flex-col gap-1">
              {NAV_LINKS.map((l) => {
                const active = isActive(l.href);

                // Parent with children → collapsible accordion row.
                if (l.children) {
                  const expanded = openGroup === l.href;
                  return (
                    <div key={l.href}>
                      <button
                        type="button"
                        onClick={() =>
                          setOpenGroup((g) => (g === l.href ? null : l.href))
                        }
                        aria-expanded={expanded}
                        className={cn(
                          "flex w-full items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-colors",
                          expanded
                            ? "bg-mp-primary/10 text-mp-primary"
                            : "text-black hover:bg-gray-100",
                        )}
                      >
                        {l.label}
                        <ChevronDown
                          className={cn(
                            "size-4 transition-transform duration-200",
                            expanded && "rotate-180",
                          )}
                        />
                      </button>
                      {expanded ? (
                        <div className="ml-3 mt-1 flex flex-col gap-1 border-l border-gray-200 pl-3">
                          {l.children.map((c) => (
                            <Link
                              key={c.label}
                              href={c.href}
                              className="rounded-xl px-4 py-2.5 text-sm text-black transition-colors hover:bg-gray-100 hover:text-mp-primary"
                            >
                              {c.label}
                            </Link>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                }

                // Leaf item → plain link.
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    className={cn(
                      "block rounded-xl px-4 py-3 text-sm font-medium transition-colors",
                      active
                        ? "bg-mp-primary/10 font-semibold text-mp-primary"
                        : "text-black hover:bg-gray-100",
                    )}
                  >
                    {l.label}
                  </Link>
                );
              })}
            </nav>
            <div className="mt-2 flex gap-2 border-t border-gray-200 pt-3">
              <Link
                href="/login"
                className="flex-1 rounded-xl bg-gray-100 px-4 py-3 text-center text-sm font-medium text-black transition-colors hover:bg-gray-200"
              >
                Login
              </Link>
              <Link
                href="/register"
                className="flex-1 rounded-xl bg-mp-primary px-4 py-3 text-center text-sm font-semibold text-white"
              >
                Open Account
              </Link>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
