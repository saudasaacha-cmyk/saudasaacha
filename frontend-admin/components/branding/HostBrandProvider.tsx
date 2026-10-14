"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { HostBranding } from "@/lib/useHostBranding";

/**
 * Host branding resolved on the SERVER, handed to the client tree.
 *
 * The login screens used to discover their brand with a client-side
 * fetch, so the first paint was always the platform's name and logo and
 * then it swapped — on a slow connection a white-labelled admin's staff
 * watched somebody else's brand for a beat, and the tab title only
 * corrected once JS ran. `app/(auth)/layout.tsx` now resolves the brand
 * from the Host header and seeds it here, so there is nothing to swap.
 *
 * `null` means "nobody seeded this" (the authed shell, which is outside
 * the auth layout) and `useHostBranding` falls back to its fetch.
 */
const HostBrandContext = createContext<HostBranding | null>(null);

export function HostBrandProvider({
  value,
  children,
}: {
  value: HostBranding;
  children: ReactNode;
}) {
  return (
    <HostBrandContext.Provider value={value}>{children}</HostBrandContext.Provider>
  );
}

export function useSeededHostBrand(): HostBranding | null {
  return useContext(HostBrandContext);
}
