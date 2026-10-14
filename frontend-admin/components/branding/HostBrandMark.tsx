"use client";

import { API_URL } from "@/lib/constants";
import { BrandLogo } from "@/components/layout/BrandLogo";
import type { HostBranding } from "@/lib/useHostBranding";

/**
 * Brand mark for the PRE-LOGIN screens.
 *
 * `BrandLogo` reads the brand off the auth store, which is empty before
 * sign-in — so on a tenant's own admin host (`admin.<their-domain>`) the
 * login screens showed the platform wordmark to people who have never
 * heard of the platform. Here the brand comes from the HOST instead,
 * resolved by `useHostBranding`, and falls back to `BrandLogo` on the
 * platform's own host where no tenant owns the domain.
 *
 * Takes the resolved branding as a prop rather than calling the hook so
 * a page that also needs `brand_name` for its copy fetches it once.
 */
export function HostBrandMark({ brand }: { brand: HostBranding }) {
  if (!brand.brand_name && !brand.logo_url) {
    return <BrandLogo href={null} size="md" showAdminBadge={false} />;
  }
  const logo = brand.logo_url
    ? brand.logo_url.startsWith("http")
      ? brand.logo_url
      : `${API_URL}${brand.logo_url}`
    : null;
  return (
    <div className="flex items-center gap-2.5">
      {logo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logo} alt="" className="size-9 rounded-md object-contain" />
      ) : null}
      <span className="text-lg font-bold tracking-tight">{brand.brand_name}</span>
    </div>
  );
}
