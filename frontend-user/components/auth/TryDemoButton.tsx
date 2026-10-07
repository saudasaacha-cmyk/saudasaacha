"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, Zap } from "lucide-react";
import { AuthAPI } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";

/**
 * "Try Demo" — one tap into the shared demo account.
 *
 * Lives on BOTH auth pages now. Someone who opened Register has shown more
 * intent than someone on Login, and they were the one group with no way to
 * look around before handing over an email and a phone number.
 *
 * Shared rather than copied: the button carries its own API call, session
 * write and redirect, so the two pages cannot drift into doing the demo
 * handoff differently.
 */
export function TryDemoButton({ label = "or try for free" }: { label?: string }) {
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const [loading, setLoading] = useState(false);

  async function start() {
    setLoading(true);
    try {
      const pair = await AuthAPI.demoLogin();
      setSession(pair as any);
      toast.success("Demo account ready — ₹50,00,000 virtual balance");
      router.push("/dashboard");
    } catch {
      toast.error("Could not start demo. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="relative flex items-center">
        <div className="flex-1 border-t border-border/50" />
        <span className="mx-3 text-[10px] text-muted-foreground">{label}</span>
        <div className="flex-1 border-t border-border/50" />
      </div>
      <button
        type="button"
        onClick={start}
        disabled={loading}
        className="flex w-full items-center gap-2.5 rounded-xl border border-mp-primary/25 bg-mp-primary/5 px-3 py-2.5 text-left transition-colors hover:bg-mp-primary/10 active:scale-[0.99] disabled:pointer-events-none disabled:opacity-70"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-mp-primary text-white">
          {loading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Zap className="size-4 fill-white" />
          )}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold leading-tight text-foreground">
            {loading ? (
              "Setting up demo…"
            ) : (
              <>
                Try Demo — ₹50,00,000
                <span className="hidden lg:inline"> virtual</span>
              </>
            )}
          </span>
          <span className="hidden text-[11px] text-muted-foreground lg:block">
            No signup · Instant · Risk-free
          </span>
        </span>
        {!loading && (
          <span className="shrink-0 rounded-full bg-mp-primary/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-mp-primary">
            Free
          </span>
        )}
      </button>
    </div>
  );
}
