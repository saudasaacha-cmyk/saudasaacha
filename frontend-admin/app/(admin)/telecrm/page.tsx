"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { TeleCrmAPI, type TeleCrmSettings } from "@/lib/api";
import { useAdminAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/common/PageHeader";

const MASK = "***";

/** Shown once, next to the token field. Everything here is a thing TeleCRM
 *  drops silently rather than rejecting, so an operator who gets it wrong
 *  sees a working screen and an empty CRM. */
const SETUP_NOTES = [
  "The token must be the Async type — a Sync token answers 403 on the ingestion endpoint.",
  "The nine custom fields must already exist in TeleCRM, spelled exactly. An unknown field name is dropped without an error.",
  "A Sync token is optional and only used to test the connection without writing a lead into your CRM.",
];

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
}

export default function TeleCrmPage() {
  const me = useAdminAuthStore((s) => s.admin);
  const qc = useQueryClient();
  const isSuper = me?.role === "SUPER_ADMIN";

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "telecrm"],
    queryFn: TeleCrmAPI.get,
    enabled: isSuper,
    refetchOnWindowFocus: false,
  });

  const [form, setForm] = useState<Partial<TeleCrmSettings>>({});
  // Seeded from the server once it answers, then owned by the form. The
  // tokens arrive as `***` and are sent back unchanged unless retyped.
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      TeleCrmAPI.save({
        enabled: form.enabled,
        enterprise_id: form.enterprise_id ?? "",
        async_token: form.async_token ?? "",
        sync_token: form.sync_token ?? "",
        send_assignee: form.send_assignee,
      }),
    onSuccess: (s) => {
      setForm(s);
      qc.invalidateQueries({ queryKey: ["admin", "telecrm"] });
      toast.success("Saved.");
    },
    onError: (e: Error) => toast.error(e.message || "Could not save"),
  });

  const test = useMutation({
    mutationFn: TeleCrmAPI.test,
    onSuccess: (s) => {
      setForm(s);
      qc.invalidateQueries({ queryKey: ["admin", "telecrm"] });
      (s.last_test_ok ? toast.success : toast.error)(s.last_test_message);
    },
    onError: (e: Error) => toast.error(e.message || "Test failed"),
  });

  const syncAll = useMutation({
    mutationFn: TeleCrmAPI.syncAll,
    onSuccess: (r) =>
      r.started
        ? toast.success("Sync started — counters below update as it runs.")
        : toast.error("Configure and enable the integration first."),
    onError: (e: Error) => toast.error(e.message || "Could not start"),
  });

  if (!isSuper) {
    return (
      <div className="p-6">
        <p className="text-sm text-muted-foreground">
          TeleCRM is a platform-wide connection. Only the super admin can see it.
        </p>
      </div>
    );
  }

  const field = (
    label: string,
    key: "enterprise_id" | "async_token" | "sync_token",
    placeholder: string,
    configured?: boolean,
  ) => (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium">
        {label}
        {configured ? (
          <span className="ml-2 text-xs font-normal text-[#10b981]">saved</span>
        ) : null}
      </span>
      <input
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono"
        value={(form[key] as string) ?? ""}
        placeholder={placeholder}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        onFocus={(e) => {
          // Clear the mask on focus so typing replaces the token rather
          // than appending to three asterisks.
          if (e.target.value === MASK) setForm((f) => ({ ...f, [key]: "" }));
        }}
      />
    </label>
  );

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="TeleCRM Connect"
        description="Push clients into TeleCRM as leads. Staff accounts are never sent — the broker or admin a client sits under rides along as a field."
      />

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <>
          <section className="space-y-4 rounded-lg border border-border bg-card p-5">
            <div className="grid gap-4 md:grid-cols-2">
              {field("Enterprise ID", "enterprise_id", "from Settings → Website and API")}
              {field(
                "Async token",
                "async_token",
                "Bearer token, Async type",
                form.async_token_configured,
              )}
              {field(
                "Sync token (optional)",
                "sync_token",
                "only used to test the connection",
                form.sync_token_configured,
              )}
            </div>

            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5 size-4 accent-primary"
                checked={!!form.enabled}
                onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
              />
              <span>
                Enabled
                <span className="block text-xs text-muted-foreground">
                  Nothing is sent while this is off. New sign-ups and logins push as they
                  happen; everything is re-synced every six hours.
                </span>
              </span>
            </label>

            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5 size-4 accent-primary"
                checked={!!form.send_assignee}
                onChange={(e) => setForm((f) => ({ ...f, send_assignee: e.target.checked }))}
              />
              <span>
                Assign leads to the owning broker or admin
                <span className="block text-xs text-muted-foreground">
                  Only works if that person is already a licensed TeleCRM team member with the
                  same email. Sent only when ownership changes here — a routine sync that
                  re-asserted it would overwrite whatever your team did inside the CRM.
                </span>
              </span>
            </label>

            <ul className="space-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
              {SETUP_NOTES.map((n) => (
                <li key={n}>• {n}</li>
              ))}
            </ul>

            <div className="flex flex-wrap gap-2 pt-1">
              <Button onClick={() => save.mutate()} disabled={save.isPending}>
                {save.isPending ? "Saving…" : "Save"}
              </Button>
              <Button
                variant="outline"
                onClick={() => test.mutate()}
                disabled={test.isPending}
              >
                {test.isPending ? "Testing…" : "Test connection"}
              </Button>
              <Button
                variant="outline"
                onClick={() => syncAll.mutate()}
                disabled={syncAll.isPending || !form.enabled}
              >
                <RefreshCw className="mr-1.5 size-4" />
                Sync everyone now
              </Button>
            </div>
          </section>

          <section className="grid gap-3 rounded-lg border border-border bg-card p-5 text-sm sm:grid-cols-2">
            <div>
              <p className="text-xs uppercase text-muted-foreground">Last test</p>
              <p className={data?.last_test_ok === false ? "text-[#ef4444]" : ""}>
                {fmt(data?.last_test_at ?? null)}
                {data?.last_test_message ? ` — ${data.last_test_message}` : ""}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Last push</p>
              <p>{fmt(data?.last_push_at ?? null)}</p>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Sent</p>
              <p className="text-[#10b981]">{data?.pushed_total ?? 0}</p>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Failed</p>
              <p className={data?.failed_total ? "text-[#ef4444]" : ""}>
                {data?.failed_total ?? 0}
              </p>
            </div>
            {data?.last_error ? (
              <div className="sm:col-span-2">
                <p className="text-xs uppercase text-muted-foreground">Last error</p>
                <p className="break-words font-mono text-xs text-[#ef4444]">
                  {data.last_error}
                </p>
              </div>
            ) : null}
          </section>
        </>
      )}
    </div>
  );
}
