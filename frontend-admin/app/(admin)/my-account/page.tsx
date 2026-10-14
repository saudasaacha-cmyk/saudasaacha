"use client";

import { useState } from "react";
import { toast } from "sonner";
import { AtSign, KeyRound, Loader2, User } from "lucide-react";
import { AdminAuthAPI } from "@/lib/api";
import { useAdminAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/common/PageHeader";

/**
 * An employee's own account — the one page they always have.
 *
 * Platform settings (where admins change their password) carries no
 * employee permission, so staff had no way to change the credentials
 * their admin handed them. Both forms act on the signed-in account only;
 * the backend reads the actor off the token and never takes an id.
 */
export default function MyAccountPage() {
  const admin = useAdminAuthStore((s) => s.admin);
  const refreshMe = useAdminAuthStore((s) => s.refreshMe);

  return (
    <div className="space-y-4">
      <PageHeader
        title="My account"
        description="Your sign-in details. Changes apply to your own account only."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="size-4 text-primary" /> Who you are
            </CardTitle>
            <CardDescription>Set by the admin who created your account.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Name" value={admin?.full_name} />
            <Row label="Code" value={admin?.user_code} mono />
            <Row label="Email" value={admin?.email} />
            <Row label="Role" value={admin?.role === "EMPLOYEE" ? "Employee" : admin?.role} />
          </CardContent>
        </Card>

        <EmailCard onChanged={() => void refreshMe()} />
        <PasswordCard />
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value?: string | null;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border/40 pb-2 last:border-0 last:pb-0">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className={`min-w-0 truncate ${mono ? "font-mono text-xs" : ""}`} title={value ?? ""}>
        {value || "—"}
      </span>
    </div>
  );
}

function EmailCard({ onChanged }: { onChanged: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      const res = await AdminAuthAPI.changeEmail(password, email.trim());
      // Pull the fresh identity so the card above and the top bar show
      // the new address without a reload.
      onChanged();
      setEmail("");
      setPassword("");
      toast.success("Email updated", {
        description: `Sign in with ${res.email} next time.`,
      });
    } catch (e: any) {
      toast.error(e?.message || "Could not change the email");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AtSign className="size-4 text-primary" /> Change email
        </CardTitle>
        <CardDescription>
          This is your sign-in address, so your current password is required.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="new-email">New email</Label>
          <Input
            id="new-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email-password">Current password</Label>
          <Input
            id="email-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <Button
          type="button"
          className="w-full gap-2"
          disabled={busy || !email.trim() || password.length < 6}
          onClick={save}
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : null}
          {busy ? "Saving…" : "Update email"}
        </Button>
      </CardContent>
    </Card>
  );
}

function PasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const mismatch = confirm.length > 0 && next !== confirm;

  async function save() {
    setBusy(true);
    try {
      await AdminAuthAPI.changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      // No re-login: the token keys off the user id, not the password.
      toast.success("Password changed");
    } catch (e: any) {
      toast.error(e?.message || "Could not change the password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="size-4 text-primary" /> Change password
        </CardTitle>
        <CardDescription>
          Minimum 6 characters. You stay signed in on this device.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="cur-pw">Current password</Label>
          <Input
            id="cur-pw"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="new-pw">New password</Label>
          <Input
            id="new-pw"
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirm-pw">Confirm new password</Label>
          <Input
            id="confirm-pw"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
          {mismatch && (
            <p className="text-xs text-destructive">The two passwords don&apos;t match.</p>
          )}
        </div>
        <Button
          type="button"
          className="w-full gap-2"
          disabled={busy || current.length < 6 || next.length < 6 || next !== confirm}
          onClick={save}
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : null}
          {busy ? "Saving…" : "Update password"}
        </Button>
      </CardContent>
    </Card>
  );
}
