import { NextRequest } from "next/server";

// Dynamic Web App Manifest for the admin panel.
//
// PWA installs (Chrome / Edge / Safari "Install app") fetch the URL
// referenced by `<link rel="manifest" href="...">` AT INSTALL TIME and
// commit the icons + name into the OS launcher. To get a per-tenant
// install icon the manifest URL must vary per tenant; we do that by
// honouring a `?u=<USER_CODE>` query param injected at runtime by
// `<AdminBrandingChrome>` once the auth store hydrates.
//
// When the param is missing or the lookup fails we fall back to the
// platform-default manifest — keeping the existing UX byte-identical
// for super-admins and pre-branding installs.
//
// Note: this is a route handler (not the file-convention `manifest.ts`)
// so we can serve it dynamically. Next.js still resolves
// `/manifest.webmanifest` to this handler.

export const dynamic = "force-dynamic";
export const revalidate = 0;

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

const PLATFORM_DEFAULT = {
  name: "SachchaSauda Broker Admin",
  short_name: "MP Admin",
  description: "Super-admin control panel for the SachchaSauda Broker platform.",
  start_url: "/dashboard",
  scope: "/",
  // Standalone gives the installed app its own window without browser
  // chrome (no URL bar, no tabs) so it really feels like a native shell.
  display: "standalone",
  // Fallback chain — some browsers (Samsung Internet) still honour
  // display_override even when "standalone" is the primary value.
  display_override: ["standalone", "minimal-ui"],
  orientation: "portrait" as const,
  background_color: "#0a0a0a",
  theme_color: "#0a0a0a",
  categories: ["finance", "business"],
  // Multiple icon entries — the SVG handles any size losslessly (used
  // by Chromium / Edge desktop), but Android home screens require a
  // 192/512 raster declaration to pass the install criteria. Declaring
  // the SVG at those sizes is valid and gets rasterised by the OS.
  icons: [
    { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    { src: "/icon.svg", sizes: "192x192", type: "image/svg+xml", purpose: "any maskable" },
    { src: "/icon.svg", sizes: "512x512", type: "image/svg+xml", purpose: "any maskable" },
  ],
};

type Branding = {
  brand_name: string | null;
  logo_url: string | null;
};

async function fetchBranding(path: string): Promise<Branding | null> {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}/api/v1/branding/${path}`, {
      // Manifest fetch is unauthenticated; use the public endpoints.
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    const json = await res.json();
    const data = json?.data ?? null;
    if (!data) return null;
    return { brand_name: data.brand_name ?? null, logo_url: data.logo_url ?? null };
  } catch {
    return null;
  }
}

export async function GET(req: NextRequest) {
  const userCode = (req.nextUrl.searchParams.get("u") || "").trim().toUpperCase();
  // Pre-login there is no user code to key off — an install from a
  // tenant's own admin host would land on the home screen named
  // "MP Admin". The host itself identifies the tenant, so fall back to
  // it; `?u=` still wins once auth hydrates.
  const domain = (req.nextUrl.searchParams.get("d") || "").trim().toLowerCase();
  let manifest: Record<string, unknown> = { ...PLATFORM_DEFAULT };

  const lookup = userCode
    ? `by-code/${encodeURIComponent(userCode)}`
    : domain
      ? `by-domain?domain=${encodeURIComponent(domain)}`
      : null;

  if (lookup) {
    const brand = await fetchBranding(lookup);
    if (brand?.brand_name || brand?.logo_url) {
      const name = brand.brand_name?.trim() || PLATFORM_DEFAULT.name;
      const shortName = (brand.brand_name?.trim() || PLATFORM_DEFAULT.short_name).slice(0, 12);
      const logo = brand.logo_url ? `${API_BASE}${brand.logo_url}` : null;
      manifest = {
        ...PLATFORM_DEFAULT,
        name,
        short_name: shortName,
        description: `${name} — admin control panel`,
        icons: logo
          ? [
              // Browsers require at least one icon >= 144px to enable
              // the install prompt. We only have one source upload, so
              // we declare it at multiple sizes — the browser will
              // rasterise as needed.
              { src: logo, sizes: "192x192", type: "image/png", purpose: "any" },
              { src: logo, sizes: "512x512", type: "image/png", purpose: "any" },
              { src: logo, sizes: "any", purpose: "any" },
            ]
          : PLATFORM_DEFAULT.icons,
      };
    }
  }

  return new Response(JSON.stringify(manifest), {
    headers: {
      "Content-Type": "application/manifest+json; charset=utf-8",
      // Per-tenant content — never cache at the CDN/edge.
      "Cache-Control": "private, no-store, max-age=0",
    },
  });
}
