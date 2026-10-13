"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileSpreadsheet, FileText, Search } from "lucide-react";
import { UsersAPI, type ActiveUser } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { useAdminAuthStore } from "@/stores/authStore";

/**
 * Who can trade, and who is actually here.
 *
 * Every other user list in this panel is scoped to the caller's own pool,
 * which leaves a super admin unable to answer the one question this page
 * exists for: across the WHOLE platform — every admin's clients, every
 * broker's and sub-broker's, plus the admin-tier accounts themselves —
 * which are ACTIVE, and of those, which have the app open right now.
 *
 * Contacts are readable here rather than `••••••••`, matching the
 * super-admin user-book export. The gate is the role (enforced on the
 * server too, not just by hiding the nav item) and every file download is
 * written to the audit log.
 */
const REFETCH_MS = 20_000;

const ROLE_OPTIONS = [
  { value: "", label: "All roles" },
  { value: "CLIENT", label: "Clients" },
  { value: "BROKER", label: "Brokers & sub-brokers" },
  { value: "ADMIN", label: "Admins" },
  { value: "EMPLOYEE", label: "Employees" },
  { value: "SUPER_ADMIN", label: "Super admin" },
];

/** "3m" / "2h 14m" — how long this session has been up. */
function elapsed(epochSec: number | null): string {
  if (!epochSec) return "—";
  const secs = Math.max(0, Math.floor(Date.now() / 1000 - epochSec));
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function stampIST(value: string | number | null): string {
  if (!value) return "—";
  const d = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
    .format(d)
    .replace(",", "");
}

export default function ActiveUsersPage() {
  const me = useAdminAuthStore((s) => s.admin);
  const isSuperAdmin = me?.role === "SUPER_ADMIN";

  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [onlineOnly, setOnlineOnly] = useState(false);
  const [includeDemo, setIncludeDemo] = useState(false);
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState<"xlsx" | "pdf" | null>(null);
  const pageSize = 50;

  const filters = {
    q: q || undefined,
    role: role || undefined,
    online_only: onlineOnly,
    include_demo: includeDemo,
  };

  const { data, isFetching } = useQuery({
    queryKey: ["admin", "active-users", { q, role, onlineOnly, includeDemo, page }],
    queryFn: () => UsersAPI.active({ ...filters, page, page_size: pageSize }),
    enabled: isSuperAdmin,
    // The online column is the live half of this page; the roster half
    // barely moves. One slow poll keeps both honest without the 1.5 s
    // cadence the trading tables need.
    refetchInterval: REFETCH_MS,
    refetchOnWindowFocus: false,
  });

  async function download(format: "xlsx" | "pdf") {
    setBusy(format);
    try {
      // Whatever the page is filtered to is what the file carries, so a
      // download can't silently disagree with the screen it came from.
      const blob = await UsersAPI.activeExportFile({ ...filters, format });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      // Timestamped to the minute: "online now" means nothing without
      // knowing when "now" was.
      const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
      a.href = url;
      a.download = `active-users-${stamp}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      toast.error(e?.message || "Could not build the file");
    } finally {
      setBusy(null);
    }
  }

  // The nav item is already super-admin gated, but a typed URL isn't.
  if (!isSuperAdmin) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center text-sm text-muted-foreground">
        This page is for the super admin only.
      </div>
    );
  }

  const meta = data?.meta;
  const total = meta?.total ?? 0;
  const online = meta?.online ?? 0;
  const totalPages = meta?.total_pages ?? 1;

  const columns: Column<ActiveUser>[] = [
    {
      key: "online",
      header: "Live",
      align: "center",
      width: "64px",
      render: (r) =>
        r.online ? (
          <span className="relative inline-flex size-2 align-middle" title="App open now">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500/60" />
            <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
          </span>
        ) : (
          <span
            className="inline-block size-2 rounded-full bg-muted-foreground/30 align-middle"
            title="Not connected"
          />
        ),
    },
    {
      key: "user_code",
      header: "Code",
      render: (r) => <span className="font-mono text-xs">{r.user_code}</span>,
    },
    {
      key: "full_name",
      header: "Name",
      render: (r) => (
        <span className="flex items-center gap-1.5">
          {r.full_name || "—"}
          {r.is_demo && (
            <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-500">
              Demo
            </span>
          )}
        </span>
      ),
    },
    {
      key: "role_label",
      header: "Role",
      render: (r) => (
        <span className="text-xs text-muted-foreground">{r.role_label}</span>
      ),
    },
    {
      key: "owner",
      header: "Owner",
      className: "max-w-[200px] truncate",
      render: (r) => (
        <span className="text-xs text-muted-foreground" title={r.owner}>
          {r.owner}
        </span>
      ),
    },
    {
      key: "email",
      header: "Email",
      className: "max-w-[240px] truncate",
      render: (r) => <span className="text-xs">{r.email}</span>,
    },
    {
      key: "mobile",
      header: "Mobile",
      render: (r) => <span className="font-tabular text-xs">{r.mobile}</span>,
    },
    {
      key: "online_since",
      header: "Online for",
      align: "right",
      render: (r) =>
        r.online ? (
          <span
            className="text-xs font-semibold tabular-nums text-emerald-500"
            title={`Since ${stampIST(r.online_since)} IST`}
          >
            {elapsed(r.online_since)}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
    {
      key: "last_login_at",
      header: "Last login",
      align: "right",
      render: (r) => (
        <span className="text-xs tabular-nums text-muted-foreground">
          {r.last_login_at ? stampIST(r.last_login_at) : "never"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Active users"
        description={`${total} active account${total === 1 ? "" : "s"} across the platform · ${online} online right now`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              className="gap-2"
              disabled={busy !== null}
              loading={busy === "xlsx"}
              onClick={() => download("xlsx")}
            >
              <FileSpreadsheet className="size-4" /> Excel
            </Button>
            <Button
              className="gap-2"
              disabled={busy !== null}
              loading={busy === "pdf"}
              onClick={() => download("pdf")}
            >
              <FileText className="size-4" /> PDF
            </Button>
          </div>
        }
      />

      <p className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
        Every account with status <span className="font-semibold">ACTIVE</span> —
        your own clients, every admin&apos;s, every broker&apos;s and
        sub-broker&apos;s, plus the admin-tier logins themselves. The green dot
        is the separate question of whether their app is checked in right now
        (drops off after {meta?.ttl_sec ?? 90}s of silence). Email and phone are
        readable here and nowhere else in the panel; downloads are audit-logged.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => {
              setPage(1);
              setQ(e.target.value);
            }}
            placeholder="Search code / email / mobile / name"
            className="pl-9"
          />
        </div>
        <select
          value={role}
          onChange={(e) => {
            setPage(1);
            setRole(e.target.value);
          }}
          className="h-10 rounded-md border border-border bg-background px-3 text-sm"
        >
          {ROLE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={onlineOnly}
            onChange={(e) => {
              setPage(1);
              setOnlineOnly(e.target.checked);
            }}
          />
          Online only
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={includeDemo}
            onChange={(e) => {
              setPage(1);
              setIncludeDemo(e.target.checked);
            }}
          />
          Include demo
        </label>
      </div>

      {/* Desktop table. Phones get the card list below — nine columns
          don't survive a 360 px viewport. */}
      <div className="hidden md:block">
        <DataTable
          columns={columns}
          rows={data?.items}
          keyExtractor={(r) => r.id}
          loading={isFetching && !data}
          empty="No active accounts match the current filters."
          rowClassName={(r) => (r.online ? "bg-emerald-500/5" : undefined)}
        />
      </div>

      <div className="space-y-2 md:hidden">
        {isFetching && !data && (
          <div className="rounded-lg border border-border bg-card p-6 text-center text-sm text-muted-foreground">
            Loading…
          </div>
        )}
        {!isFetching && (data?.items?.length ?? 0) === 0 && (
          <div className="rounded-lg border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground">
            No active accounts match the current filters.
          </div>
        )}
        {data?.items?.map((r) => (
          <ActiveUserCard key={r.id} r={r} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2 text-xs text-muted-foreground">
          <span>
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Prev
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

function ActiveUserCard({ r }: { r: ActiveUser }) {
  return (
    <div
      className={`rounded-xl border p-3 ${
        r.online ? "border-emerald-500/30 bg-emerald-500/5" : "border-border bg-card"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <span className="rounded-md bg-primary/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-primary">
            {r.user_code}
          </span>
          <span className="text-[11px] text-muted-foreground">{r.role_label}</span>
          {r.is_demo && (
            <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-500">
              Demo
            </span>
          )}
        </div>
        {r.online ? (
          <span className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-500">
            Online {elapsed(r.online_since)}
          </span>
        ) : (
          <span className="shrink-0 text-[10px] text-muted-foreground">Offline</span>
        )}
      </div>

      <div className="mt-1.5 truncate text-sm font-semibold" title={r.full_name}>
        {r.full_name || "—"}
      </div>
      <div className="mt-0.5 space-y-0.5 text-[11px] text-muted-foreground">
        <div className="truncate">{r.email}</div>
        <div className="font-tabular">{r.mobile}</div>
        <div className="truncate">{r.owner}</div>
        <div>
          Last login:{" "}
          {r.last_login_at ? stampIST(r.last_login_at) : "never"}
        </div>
      </div>
    </div>
  );
}
