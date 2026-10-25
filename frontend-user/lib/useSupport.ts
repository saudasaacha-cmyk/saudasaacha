import { useMutation, useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import { useBranding } from "@/lib/branding-context";
import { APP_NAME } from "@/lib/constants";

export interface SupportContacts {
  whatsapp: string;
  /** The cash-deposit desk. The server already falls back to `whatsapp`
   *  when the chain sets no separate one, so this is never empty when
   *  `whatsapp` is not. */
  cash_deposit_whatsapp: string;
  email: string;
}

export interface UserTerms {
  text: string;
  enabled: boolean;
  needs_accept: boolean;
  accepted_at: string | null;
}

/** Resolved T&C for the logged-in user (cascades up the broker chain).
 *  Used by the Terms gate that runs once after register / on first
 *  dashboard hit if the admin enabled it and the user hasn't accepted
 *  yet (or the admin updated the text since the last accept). */
export function useUserTerms(enabled = true) {
  return useQuery<UserTerms>({
    queryKey: ["user", "terms"],
    queryFn: () => unwrap<UserTerms>(api.get("/user/support/terms")),
    enabled,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useAcceptTerms() {
  return useMutation({
    mutationFn: () => unwrap<any>(api.post("/user/support/terms/accept", {})),
  });
}

/** Admin-managed home-page ticker lines (cascades up the broker chain).
 *  Empty ⇒ the home ticker is hidden. Refetched periodically so a line the
 *  broker just added shows up without a reload. */
export function useHomeTicker() {
  return useQuery<{ messages: string[] }>({
    queryKey: ["user", "ticker"],
    queryFn: () => unwrap<{ messages: string[] }>(api.get("/user/support/ticker")),
    staleTime: 30_000,
    refetchInterval: 120_000,
    refetchOnMount: "always",
    retry: 1,
  });
}

/**
 * Admin-managed WhatsApp + support email. Pulled from `/user/support`
 * — backed by `platform.support_whatsapp` + `platform.support_email`
 * PlatformSetting rows that the admin can edit on /admin/settings/platform.
 *
 * No hardcoded fallback — admin is the single source of truth. If
 * admin clears a value, the corresponding UI affordance disappears
 * immediately. If the backend hasn't been restarted with the new
 * route, the query errors and the section hides — the fix is "restart
 * the backend so the seed inserts default support keys", not stale
 * defaults in the JS bundle.
 *
 * Generously cached because these change at most once a quarter.
 */
export function useSupportContacts() {
  return useQuery<SupportContacts>({
    queryKey: ["support", "contacts"],
    queryFn: () => unwrap<SupportContacts>(api.get("/user/support")),
    // Admins set/change their support WhatsApp actively, so don't cache it for
    // long — refetch on every page mount so the number a broker just saved is
    // visible to their users right away (was 10 min stale → looked "not set").
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  });
}

/** wa.me URL builder — strips formatting from the admin-stored number
 *  (spaces, dashes, leading "+") since wa.me expects digits only.
 *  Returns null for unusable input so callers can hide the link. */
export function buildWhatsappUrl(
  raw: string | undefined | null,
  prefill?: string,
): string | null {
  if (!raw) return null;
  const digits = String(raw).replace(/[^0-9]/g, "");
  if (digits.length < 8) return null;
  const text = prefill ? `?text=${encodeURIComponent(prefill)}` : "";
  return `https://wa.me/${digits}${text}`;
}

export function buildMailtoUrl(
  email: string | undefined | null,
  opts?: { subject?: string; body?: string },
): string | null {
  if (!email || !email.includes("@")) return null;
  const params: string[] = [];
  if (opts?.subject) params.push(`subject=${encodeURIComponent(opts.subject)}`);
  if (opts?.body) params.push(`body=${encodeURIComponent(opts.body)}`);
  const qs = params.length > 0 ? `?${params.join("&")}` : "";
  return `mailto:${email}${qs}`;
}

/**
 * The support WhatsApp link, with a message prefilled in the brand the
 * USER is actually signed in to.
 *
 * It used to be the string "Hi, I need help with my RIZING BULL
 * account", repeated at three call sites — so a Rising Bull customer
 * opened a chat with their own broker introducing themselves as a
 * customer of somebody else.
 *
 * Falls back to the platform name only where the rest of the app does
 * (`showPlatformDefault`); on a tenant's domain with the brand not yet
 * resolved the message stays generic rather than naming the super
 * admin.
 */
export function useBrandName(): string {
  const { branding, showPlatformDefault } = useBranding();
  return (
    (branding?.brand_name ?? "").trim() || (showPlatformDefault ? APP_NAME : "")
  );
}

export function useSupportWhatsappUrl(): string | null {
  const { data: support } = useSupportContacts();
  const name = useBrandName();
  const prefill = name
    ? `Hi, I need help with my ${name} account`
    : "Hi, I need help with my account";
  return buildWhatsappUrl(support?.whatsapp, prefill);
}

/** Same as `useSupportWhatsappUrl`, for the deposit screen's own ask. */
export function useDepositSupportPrefill(): string {
  const name = useBrandName();
  return name
    ? `Hi, I need help adding funds to my ${name} account`
    : "Hi, I need help adding funds to my account";
}

/** The WhatsApp hand-off for a cash deposit the user just submitted.
 *
 *  Cash is the one mode with nothing for support to look up — no UTR, no
 *  bank row, no gateway reference. So the message carries everything the
 *  person on the other end would otherwise have to ask for, in the brand
 *  the user is actually signed in to.
 *
 *  Returns null when the admin has set no WhatsApp number, so the caller
 *  can simply skip the hand-off rather than opening a broken link.
 */
export function useCashDepositWhatsapp(): (d: {
  amount: number;
  city: string;
  area: string;
  note?: string;
  userCode?: string;
  userName?: string;
}) => string | null {
  const { data: support } = useSupportContacts();
  const name = useBrandName();
  return (d) => {
    const lines = [
      name ? `Cash deposit submitted — ${name}` : "Cash deposit submitted",
      "",
      `Amount: Rs ${d.amount}`,
      `City: ${d.city}`,
      `Area: ${d.area}`,
    ];
    if (d.note) lines.push(`Notes: ${d.note}`);
    if (d.userCode) lines.push(`Client code: ${d.userCode}`);
    if (d.userName) lines.push(`Name: ${d.userName}`);
    lines.push("", "Receipt uploaded in the app. Please verify and approve.");
    // The cash desk, not support — see `SupportContacts`.
    return buildWhatsappUrl(
      support?.cash_deposit_whatsapp || support?.whatsapp,
      lines.join("\n"),
    );
  };
}

/** The WhatsApp hand-off for a cash WITHDRAWAL the user just requested.
 *
 *  Same reasoning as the deposit one: cash has no account and no
 *  reference, so support would otherwise have to ask for every field
 *  before they could arrange the handover.
 */
export function useCashWithdrawalWhatsapp(): (d: {
  amount: number;
  city: string;
  area: string;
  note?: string;
  userCode?: string;
  userName?: string;
}) => string | null {
  const { data: support } = useSupportContacts();
  const name = useBrandName();
  return (d) => {
    const lines = [
      name ? `Cash withdrawal requested — ${name}` : "Cash withdrawal requested",
      "",
      `Amount: Rs ${d.amount}`,
      `Collect at — City: ${d.city}`,
      `Area: ${d.area}`,
    ];
    if (d.note) lines.push(`Remarks: ${d.note}`);
    if (d.userCode) lines.push(`Client code: ${d.userCode}`);
    if (d.userName) lines.push(`Name: ${d.userName}`);
    lines.push("", "Awaiting approval. Please confirm the handover.");
    return buildWhatsappUrl(
      support?.cash_deposit_whatsapp || support?.whatsapp,
      lines.join("\n"),
    );
  };
}

/** Per-category alert tones, set by the admin in Platform Settings. */
export function fetchNotifySounds() {
  return unwrap<Record<string, string>>(api.get("/user/support/notify-sounds"));
}
