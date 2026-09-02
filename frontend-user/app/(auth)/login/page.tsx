"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Eye, EyeOff, Loader2, Mail, Lock, Send, ShieldCheck, Smartphone, Wrench, Zap } from "lucide-react";
import { useBranding } from "@/lib/branding-context";
import { useAuthStore } from "@/stores/authStore";
import { ApiError, AuthAPI, ProfileAPI, setTokens } from "@/lib/api";
import { STORAGE_KEYS } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { InstallPwaButton } from "@/components/common/InstallPwaButton";

const schema = z.object({
  identifier: z.string().min(3, "Enter your email or mobile"),
  password: z.string().min(8, "Minimum 8 characters"),
  two_fa_code: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginSplash subtitle="Loading…" />}>
      <LoginPageInner />
    </Suspense>
  );
}

function LoginSplash({ subtitle }: { subtitle: string }) {
  return (
    <div className="flex min-h-[280px] flex-col items-center justify-center gap-3 text-center">
      <div className="grid size-12 place-items-center rounded-2xl bg-primary/10">
        <Loader2 className="size-5 animate-spin text-primary" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">Signing you in…</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
    </div>
  );
}

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((s) => s.login);
  const setUser = useAuthStore((s) => s.setUser);
  const hydrated = useAuthStore((s) => s.hydrated);
  const currentUser = useAuthStore((s) => s.user);
  const setSession = useAuthStore((s) => s.setSession);
  const [showPwd, setShowPwd] = useState(false);
  const [needs2fa, setNeeds2fa] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  // Maintenance popup — shown both when a live session gets kicked here
  // (?maintenance=1, set by the api interceptor) and when a fresh login is
  // rejected with MAINTENANCE_MODE below.
  const [maintenanceMsg, setMaintenanceMsg] = useState<string | null>(null);
  useEffect(() => {
    if (searchParams?.get("maintenance") === "1") {
      setMaintenanceMsg(
        "The platform is under maintenance. Please try again later.",
      );
    }
  }, [searchParams]);

  // Capture a shared referral link's ?ref= BEFORE the user tries the demo,
  // so admin/broker/sub-broker attribution survives demo-login → logout →
  // register (the URL query is lost across those hops). Persisted under a key
  // clearTokens() never touches; the register page consumes it on signup.
  const urlRef = (searchParams?.get("ref") || "").trim().toUpperCase();
  useEffect(() => {
    if (typeof window !== "undefined" && urlRef) {
      window.localStorage.setItem(STORAGE_KEYS.referralCode, urlRef);
    }
  }, [urlRef]);

  useEffect(() => {
    if (!hydrated || !currentUser) return;
    const hasRefresh =
      typeof window !== "undefined" &&
      !!window.localStorage.getItem(STORAGE_KEYS.refreshToken);
    if (hasRefresh) {
      router.replace("/dashboard");
    } else {
      try {
        window.localStorage.removeItem("nb.auth");
      } catch {
        /* ignore */
      }
      setUser(null);
    }
  }, [hydrated, currentUser, router, setUser]);

  const impAccess = searchParams?.get("access");
  const impRefresh = searchParams?.get("refresh");
  const isImpersonating = !!(impAccess && impRefresh);
  const [impersonationFailed, setImpersonationFailed] = useState(false);

  useEffect(() => {
    if (!isImpersonating || !impAccess || !impRefresh) return;
    setTokens(impAccess, impRefresh);
    router.prefetch("/dashboard");
    ProfileAPI.me()
      .then((u: any) => {
        setUser(u as any);
        router.replace("/dashboard");
      })
      .catch(() => {
        toast.error("Impersonation token rejected");
        setImpersonationFailed(true);
      });
  }, [isImpersonating, impAccess, impRefresh, router, setUser]);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { identifier: "", password: "", two_fa_code: "" },
  });

  async function handleDemoLogin() {
    setDemoLoading(true);
    try {
      const pair = await AuthAPI.demoLogin();
      setSession(pair as any);
      toast.success("Demo account ready — ₹50,00,000 virtual balance");
      router.push("/dashboard");
    } catch {
      toast.error("Could not start demo. Please try again.");
    } finally {
      setDemoLoading(false);
    }
  }

  async function onSubmit(values: FormValues) {
    try {
      await login(values.identifier, values.password, values.two_fa_code || undefined);
      toast.success("Welcome back");
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "TWO_FA_REQUIRED") {
          setNeeds2fa(true);
          toast.info("Enter your 2FA code to continue");
          return;
        }
        if (err.code === "MAINTENANCE_MODE") {
          // Pool locked by the admin → prominent popup, not a toast.
          setMaintenanceMsg(err.message);
          return;
        }
        toast.error(err.message);
      } else {
        toast.error("Login failed. Please try again.");
      }
    }
  }

  if (isImpersonating && !impersonationFailed) {
    return <LoginSplash subtitle="Redirecting to your dashboard" />;
  }

  if (!hydrated) {
    return <LoginSplash subtitle="Restoring your session…" />;
  }

  if (currentUser) {
    return <LoginSplash subtitle="Redirecting to your dashboard" />;
  }

  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Maintenance popup — pool locked by the admin. Blocks login and is
          also shown when a live session was just kicked (?maintenance=1). */}
      {maintenanceMsg && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setMaintenanceMsg(null)}
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-card p-6 text-center shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-amber-500/15 text-amber-500">
              <Wrench className="size-6" />
            </div>
            <h3 className="text-lg font-semibold">Under maintenance</h3>
            <p className="mt-1.5 text-sm text-muted-foreground">{maintenanceMsg}</p>
            <Button className="mt-5 w-full" onClick={() => setMaintenanceMsg(null)}>
              OK
            </Button>
          </div>
        </div>
      )}
      {/* Compact header on mobile — tab bar in layout already labels
          the page, so headline + sub-line are sized just enough for
          context. Desktop keeps the larger treatment since there's
          no tab bar above. */}
      <div className="space-y-1">
        <h2 className="text-lg font-bold tracking-tight lg:text-3xl">
          Welcome back
        </h2>
        <p className="text-xs text-muted-foreground lg:text-sm">
          Sign in to your trading account to continue.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-3 lg:space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="identifier" className="text-xs font-medium lg:text-sm">
            Email or Mobile
          </Label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="identifier"
              placeholder="you@example.com or 9999900000"
              autoComplete="username"
              className="h-10 rounded-lg border-border/60 bg-muted/40 pl-9 text-sm transition-colors focus:border-primary/50 focus:bg-background lg:h-12 lg:rounded-xl lg:pl-10"
              {...form.register("identifier")}
            />
          </div>
          {form.formState.errors.identifier && (
            <p className="text-xs text-destructive">{form.formState.errors.identifier.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password" className="text-xs font-medium lg:text-sm">
              Password
            </Label>
            <Link href="/forgot-password" className="text-xs font-medium text-primary hover:text-primary/80">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="password"
              type={showPwd ? "text" : "password"}
              autoComplete="current-password"
              className="h-10 rounded-lg border-border/60 bg-muted/40 pl-9 pr-10 text-sm transition-colors focus:border-primary/50 focus:bg-background lg:h-12 lg:rounded-xl lg:pl-10 lg:pr-12"
              {...form.register("password")}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground transition-colors hover:text-foreground"
              onClick={() => setShowPwd((v) => !v)}
              aria-label={showPwd ? "Hide password" : "Show password"}
            >
              {showPwd ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
          {form.formState.errors.password && (
            <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>
          )}
        </div>

        {needs2fa && (
          <div className="space-y-2">
            <Label htmlFor="two_fa_code" className="text-sm font-medium">
              2FA Code
            </Label>
            <div className="relative">
              <ShieldCheck className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="two_fa_code"
                inputMode="numeric"
                maxLength={6}
                placeholder="123456"
                autoComplete="one-time-code"
                className="h-12 rounded-xl border-border/60 bg-muted/40 pl-10 text-sm transition-colors focus:border-primary/50 focus:bg-background"
                {...form.register("two_fa_code")}
              />
            </div>
          </div>
        )}

        <Button
          type="submit"
          className="h-11 w-full rounded-lg border-0 bg-gradient-to-r from-[#16A34A] to-[#22C55E] text-sm font-semibold text-white shadow-lg shadow-green-500/30 transition-opacity hover:opacity-95 lg:h-12 lg:rounded-xl"
          loading={form.formState.isSubmitting}
        >
          Sign in
        </Button>
      </form>

      {/* Demo account CTA — minimalist green */}
      <div className="space-y-2">
        <div className="relative flex items-center">
          <div className="flex-1 border-t border-border/50" />
          <span className="mx-3 text-[10px] text-muted-foreground">or try for free</span>
          <div className="flex-1 border-t border-border/50" />
        </div>
        <button
          type="button"
          onClick={handleDemoLogin}
          disabled={demoLoading}
          className="flex w-full items-center gap-2.5 rounded-xl border border-mp-primary/25 bg-mp-primary/5 px-3 py-2.5 text-left transition-colors hover:bg-mp-primary/10 active:scale-[0.99] disabled:pointer-events-none disabled:opacity-70"
        >
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-mp-primary text-white">
            {demoLoading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Zap className="size-4 fill-white" />
            )}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold leading-tight text-foreground">
              {demoLoading ? (
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
          {!demoLoading && (
            <span className="shrink-0 rounded-full bg-mp-primary/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-mp-primary">
              Free
            </span>
          )}
        </button>
      </div>

      {/* Footer — "no account?" link + minimalist Install App CTA */}
      <div className="space-y-3">
        <p className="text-center text-xs text-muted-foreground lg:text-sm">
          Don&apos;t have an account?{" "}
          <Link
            href={urlRef ? `/register?ref=${encodeURIComponent(urlRef)}` : "/register"}
            className="font-semibold text-mp-primary hover:text-mp-primary/80"
          >
            Create one
          </Link>
        </p>

        <InstallAppBanner />
        <TelegramBanner />
      </div>
    </div>
  );
}

/** Per-admin Telegram button — shows ONLY when the resolved brand (this
 *  admin's referral / custom domain) has a telegram_link set. Renders http(s)
 *  links only so a stored value can never become a javascript: href. */
function TelegramBanner() {
  const { branding } = useBranding();
  const link = (branding?.telegram_link ?? "").trim();
  if (!link || !/^https?:\/\//i.test(link)) return null;
  return (
    <a
      href={link}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2.5 rounded-xl border border-[#229ED9]/30 bg-[#229ED9]/10 px-3 py-2.5 transition-colors hover:bg-[#229ED9]/20"
    >
      <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-[#229ED9]/15 text-[#229ED9]">
        <Send className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold leading-tight text-foreground">Join us on Telegram</p>
        <p className="hidden text-[11px] text-muted-foreground lg:block">Updates, support &amp; help.</p>
      </div>
    </a>
  );
}

/** Attractive "Install SaudaSaacha App" promo banner used on the auth
 *  pages.  Wraps InstallPwaButton's click logic but renders a much
 *  richer surface — gradient ring, app icon tile, headline + sub-line,
 *  arrow chevron — so users actually notice it. */
function InstallAppBanner() {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-border/60 bg-muted/30 px-3 py-2.5">
      <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-mp-primary/10 text-mp-primary">
        <Smartphone className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold leading-tight text-foreground">
          Get the app
        </p>
        <p className="hidden text-[11px] text-muted-foreground lg:block">
          Faster orders, one-tap login.
        </p>
      </div>
      <InstallPwaButton
        variant="compact"
        className="shrink-0 !border-mp-primary/30 !bg-mp-primary/10 !text-mp-primary hover:!bg-mp-primary/20"
      />
    </div>
  );
}
