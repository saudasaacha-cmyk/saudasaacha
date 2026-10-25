export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME ?? "RIZING BULL Admin";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Derive WS origin from `API_URL` when `NEXT_PUBLIC_WS_URL` is unset —
 *  see the matching helper in `frontend-user/lib/constants.ts` for the
 *  full rationale. Short version: ops keeps forgetting to set
 *  `NEXT_PUBLIC_WS_URL` on the EC2, the build embeds `ws://localhost:8000`,
 *  the admin's live admin-event stream fails silently in production. */
function _deriveWsFromApi(api: string): string {
  if (api.startsWith("https://")) return "wss://" + api.slice("https://".length);
  if (api.startsWith("http://")) return "ws://" + api.slice("http://".length);
  return "ws://localhost:8000";
}
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? _deriveWsFromApi(API_URL);
export const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY ?? "";

export const STORAGE_KEYS = {
  accessToken: "nb.admin.accessToken",
  refreshToken: "nb.admin.refreshToken",
  user: "nb.admin.user",
  // Which of the two sign-in screens this browser last used — see
  // lib/signin-path.ts. Survives logout on purpose: it is what sends a
  // signed-out employee back to /employee-login instead of /login.
  lastPortal: "nb.admin.lastPortal",
} as const;

/**
 * localStorage key for the persisted React Query cache (see
 * `app/providers.tsx`). Lives here rather than next to the provider so
 * the auth store can wipe it without importing a component module —
 * that import would close a cycle (providers → AdminBrandingChrome →
 * authStore). Bump the version to bust every client's cache after a
 * breaking schema change.
 *
 * Anything identity-scoped must be cleared from it when the signed-in
 * admin changes: it survives a browser close, so otherwise one admin's
 * cached lists get rehydrated into the next admin's panel.
 */
export const ADMIN_RQ_CACHE_KEY = "mp-admin-rq-cache-v1";

export const ADMIN_ROUTES = {
  login: "/login",
  dashboard: "/dashboard",
  users: "/users",
  segmentSettings: "/segment-settings/global",
  orders: "/orders",
  positions: "/positions",
  trades: "/trades",
  payinDeposits: "/payin-out/deposits",
  payinWithdrawals: "/payin-out/withdrawals",
  ledger: "/ledger",
  reports: "/reports/users",
  settingsPlatform: "/settings/platform",
  audit: "/audit",
  backup: "/backup",
} as const;
