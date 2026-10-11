"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/constants";

export type HostBranding = { brand_name: string | null; logo_url: string | null };

/**
 * Tenant branding for the host this page is being served on.
 *
 * The signed-in shell reads the brand off the auth payload, but the
 * LOGIN page runs before there is one — so on admin.<tenant-domain> it
 * fell back to the platform name and a broker's own admins were greeted
 * by somebody else's brand.
 *
 * Unauthenticated on purpose: that is what `/branding/by-domain` is
 * for, and the login screen has no token yet. No platform-host list to
 * keep in sync — on the platform's own host no admin owns that domain,
 * so the endpoint 404s and the caller keeps its platform default.
 * Same on any failure: nothing here can break the login form.
 */
export function useHostBranding(): HostBranding {
  const [brand, setBrand] = useState<HostBranding>({ brand_name: null, logo_url: null });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const host = window.location.hostname.toLowerCase();
    if (!host || host === "localhost" || host === "127.0.0.1") return;

    let cancelled = false;
    fetch(`${API_URL}/api/v1/branding/by-domain?domain=${encodeURIComponent(host)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((body) => {
        const d = body?.data;
        if (cancelled || !d) return;
        setBrand({ brand_name: d.brand_name ?? null, logo_url: d.logo_url ?? null });
      })
      .catch(() => {
        /* platform default stands */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return brand;
}
