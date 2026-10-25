import type { Metadata } from "next";
import { headers } from "next/headers";
import { HostBrandProvider } from "@/components/branding/HostBrandProvider";
import type { HostBranding } from "@/lib/useHostBranding";

/**
 * Login screens, branded from the HOST on the server.
 *
 * These two pages run before there is a signed-in admin to read a brand
 * from, so everything used to fall back to the platform: the tab title
 * said "RIZING BULL Admin" and the card showed the platform
 * wordmark on `admin.<tenant-domain>`, correcting itself only once a
 * client-side fetch landed. Resolving the brand here — from the Host
 * header, before a byte is sent — means the first paint is already the
 * tenant's, with nothing to swap.
 *
 * Cost: `headers()` opts these two routes out of static rendering. That
 * is why this lives in the (auth) group rather than the root layout,
 * where it would make all 57 admin routes dynamic for a tab title.
 */

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

const NONE: HostBranding = { brand_name: null, logo_url: null };

async function brandForHost(): Promise<HostBranding> {
  const host = (headers().get("host") || "").split(":")[0].toLowerCase();
  if (!host || !API_BASE || host === "localhost" || host === "127.0.0.1") {
    return NONE;
  }
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/branding/by-domain?domain=${encodeURIComponent(host)}`,
      // 5 min of data cache: branding changes rarely and the login screen
      // is the most-hit page on a tenant host.
      { next: { revalidate: 300 } },
    );
    if (!res.ok) return NONE;
    const data = (await res.json())?.data;
    return {
      brand_name: data?.brand_name ?? null,
      logo_url: data?.logo_url ?? null,
    };
  } catch {
    // The platform default stands — nothing here may break sign-in.
    return NONE;
  }
}

export async function generateMetadata(): Promise<Metadata> {
  const { brand_name } = await brandForHost();
  // Empty object inherits the platform title from the root layout, which
  // is exactly right on the platform's own host.
  if (!brand_name) return {};
  return {
    title: { absolute: brand_name },
    description: `${brand_name} — sign in to the control panel.`,
  };
}

export default async function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <HostBrandProvider value={await brandForHost()}>{children}</HostBrandProvider>;
}
