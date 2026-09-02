"use client";

// Soft two-tone "ding" for admin live notifications (new deposit / withdrawal
// request). Pure Web Audio — no asset file to ship or cache. Best-effort:
// silently no-ops if the browser blocks audio until the first user gesture,
// so the toast still shows even when the chime can't play.

let _ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  try {
    const AC =
      window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    if (!_ctx) _ctx = new AC();
    if (_ctx.state === "suspended") void _ctx.resume();
    return _ctx;
  } catch {
    return null;
  }
}

/**
 * Native OS notification (Android tray / Windows action center / macOS
 * banner). Falls through silently when the browser hasn't been granted
 * permission, so the in-app toast is still the source of truth — this
 * just adds the OS-level surface so an admin who minimised the PWA
 * still gets the WhatsApp-style buzz.
 *
 * Web Notifications API only fires when the page is alive (foreground
 * OR backgrounded but the process is still running). To wake a fully
 * closed PWA we'd need Web Push + FCM / VAPID and a service worker —
 * tracked as a follow-up.
 */
export function showNativeNotification(
  title: string,
  body: string,
  opts?: { onClick?: () => void; tag?: string; url?: string },
): void {
  if (typeof window === "undefined" || typeof Notification === "undefined") return;
  if (Notification.permission !== "granted") return;
  // Prefer the service worker path — Android Chrome PWAs silently drop
  // `new Notification(...)` called directly from the page; only
  // `ServiceWorkerRegistration.showNotification()` actually surfaces
  // in the system tray. postMessage the SW with the payload and let
  // it call showNotification on our behalf (see public/sw.js).
  // Falls back to direct Notification for desktop / when SW isn't
  // controlling the page yet.
  const url = opts?.url ?? window.location.pathname;
  if (
    "serviceWorker" in navigator &&
    navigator.serviceWorker.controller
  ) {
    try {
      navigator.serviceWorker.controller.postMessage({
        type: "notify",
        title,
        body,
        tag: opts?.tag,
        url,
      });
      return;
    } catch {
      // fall through to direct Notification
    }
  }
  try {
    const n = new Notification(title, {
      body,
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      tag: opts?.tag,
      renotify: true,
      requireInteraction: false,
      silent: false,
    } as NotificationOptions);
    n.onclick = () => {
      window.focus();
      try { opts?.onClick?.(); } catch {}
      n.close();
    };
  } catch {
    // older Android Chrome throws if PWA isn't installed — silent fallback
  }
}

/** Ask the OS for notification permission once. Idempotent — returns
 *  immediately if the user has already granted or denied. Safe to call
 *  on every WS bridge mount; the actual prompt only shows the first
 *  time a session reaches this code. */
export async function ensureNotificationPermission(): Promise<boolean> {
  if (typeof window === "undefined" || typeof Notification === "undefined") return false;
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;
  try {
    const res = await Notification.requestPermission();
    return res === "granted";
  } catch {
    return false;
  }
}


// ── Web Push subscription ───────────────────────────────────────────
/** Decode a base64url-encoded VAPID public key into the Uint8Array the
 *  browser's `pushManager.subscribe` expects. */
function _urlBase64ToUint8(s: string): Uint8Array {
  const padded = s + "=".repeat((4 - (s.length % 4)) % 4);
  const b64 = padded.replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

/** Subscribe this browser/PWA to backend-sent Web Push messages. Call
 *  AFTER `ensureNotificationPermission()` returns true. Idempotent — a
 *  re-subscribe with the same endpoint just refreshes the row backend-
 *  side. Best-effort: any failure (VAPID key not configured, push
 *  service down, browser doesn't support Push) is swallowed and
 *  logged; the in-app toast + tray notification still work, only the
 *  "wake fully-closed PWA" channel is missing. */
export async function subscribeForWebPush(): Promise<boolean> {
  try {
    if (typeof window === "undefined") return false;
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return false;
    if (Notification.permission !== "granted") return false;

    // Lazy import to keep this file usable in non-PWA pages where the
    // API client isn't bundled (e.g. /login).
    const { PushAPI } = await import("@/lib/api");
    const { public_key } = await PushAPI.vapidKey();
    if (!public_key) {
      console.info("[push] backend has no VAPID public key — skipping subscribe");
      return false;
    }

    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        // TS lib.d.ts wants BufferSource — Uint8Array IS one at runtime
        // but the type-narrowed signature trips on SharedArrayBuffer.
        // Cast through the underlying buffer to satisfy strict mode.
        applicationServerKey: _urlBase64ToUint8(public_key).buffer as ArrayBuffer,
      });
    }

    const raw = sub.toJSON() as { endpoint?: string; keys?: { p256dh?: string; auth?: string } };
    if (!raw.endpoint || !raw.keys?.p256dh || !raw.keys?.auth) return false;
    await PushAPI.subscribe({
      endpoint: raw.endpoint,
      keys: { p256dh: raw.keys.p256dh, auth: raw.keys.auth },
      label: navigator.userAgent.slice(0, 80),
    });
    return true;
  } catch (e) {
    console.warn("[push] subscribe failed", e);
    return false;
  }
}

export function playNotifyPing(): void {
  const ctx = getCtx();
  if (!ctx) return;
  try {
    const now = ctx.currentTime;
    const gain = ctx.createGain();
    gain.connect(ctx.destination);
    // Gentle envelope — a chime, not a buzzer.
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.16, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.55);

    // Two notes lifting upward for a friendly "ding-dong".
    const notes: Array<[number, number]> = [
      [880, 0],
      [1320, 0.12],
    ];
    for (const [freq, at] of notes) {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = freq;
      osc.connect(gain);
      osc.start(now + at);
      osc.stop(now + at + 0.42);
    }
  } catch {
    // audio is best-effort — never let it break the notification
  }
}
