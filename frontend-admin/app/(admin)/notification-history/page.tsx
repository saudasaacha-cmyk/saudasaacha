"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Search, Send } from "lucide-react";
import {
  NotificationsAPI,
  type SentNotification,
  type SentRecipient,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { Pagination } from "@/components/common/Pagination";
import { useAdminAuthStore } from "@/stores/authStore";
import { canSee } from "@/lib/permissions";

/**
 * What was sent TO USERS, and who got it.
 *
 * The history half of /send-notification, plus the sends nobody typed —
 * chart lines being saved, payment details changing. One row per SEND:
 * `Notification` is one document per recipient, so a 674-user broadcast is
 * 674 documents written in the same millisecond, and the backend folds them
 * back together by (title, message, level, source, sender, second). Clicking
 * a row unfolds it again into the recipient list.
 *
 * Scope is the usual one — an admin or broker sees the sends that reached
 * their own users; the super admin sees the platform, because the point of
 * the screen for the owner is auditing what their admins are sending.
 *
 * The 90-day ceiling below is not a UI choice: `notifications` carries a TTL
 * index on `expires_at`, so older sends no longer exist to show. Say it on
 * the page — an operator who doesn't know will read it as data loss.
 */
const PAGE_SIZE = 20;
const RECIPIENTS_PAGE_SIZE = 50;

/** Labels for the slugs the backend derives — keep in step with it. */
const SOURCES = [
  { value: "", label: "All sources" },
  { value: "admin_broadcast", label: "Admin broadcast" },
  { value: "chart_lines", label: "Chart lines" },
  { value: "payment_details", label: "Payment details" },
  { value: "zerodha_auto_login", label: "Zerodha auto-login" },
  { value: "system", label: "System" },
];

/** No "90 days" option: that IS the default, since nothing older survives. */
const DAY_OPTIONS = [
  { value: "", label: "Last 90 days" },
  { value: "1", label: "Last 24 hours" },
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
];

/** Same four tones as the composer's level picker. */
const LEVEL_TONE: Record<string, string> = {
  INFO: "border-blue-500/40 text-blue-500",
  SUCCESS: "border-emerald-500/40 text-emerald-500",
  WARNING: "border-amber-500/40 text-amber-500",
  DANGER: "border-destructive/40 text-destructive",
};

function sourceLabel(slug: string): string {
  return SOURCES.find((s) => s.value === slug)?.label ?? slug;
}

function stampIST(value: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return String(value);
  }
}

function LevelBadge({ level }: { level: string }) {
  return (
    <span
      className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${
        LEVEL_TONE[level] ?? "border-border text-muted-foreground"
      }`}
    >
      {level}
    </span>
  );
}

/** "12 / 674 · 2%" — read against delivered. */
function ReadCount({ read, total }: { read: number; total: number }) {
  const pct = total > 0 ? Math.round((read / total) * 100) : 0;
  return (
    <span className="tabular-nums text-xs">
      <span className={read > 0 ? "font-semibold text-emerald-500" : "text-muted-foreground"}>
        {read}
      </span>
      <span className="text-muted-foreground"> / {total}</span>
      <span className="ml-1 text-[10px] text-muted-foreground">({pct}%)</span>
    </span>
  );
}

export default function NotificationHistoryPage() {
  const me = useAdminAuthStore((s) => s.admin);
  // Same gate as the composer and the rest of the user lists: if you can
  // send to a pool, you can audit what reached it. Enforced server-side too.
  const allowed = canSee(me, "users");
  // A super admin is looking at the whole platform here, not at a pool —
  // every count and every empty state has to say which.
  const scopeLabel =
    me?.role === "SUPER_ADMIN" ? "platform-wide" : "to your users";

  const [q, setQ] = useState("");
  // Debounced because the super-admin arm of /sent has no `created_at`
  // index to lean on and `$group` is a blocking stage — one scan per
  // keystroke is a self-inflicted load test on a live box.
  const [qDebounced, setQDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q.trim()), 350);
    return () => clearTimeout(t);
  }, [q]);
  const [source, setSource] = useState("");
  const [days, setDays] = useState("");
  const [page, setPage] = useState(1);
  // The send whose recipients are open, held whole: the drill-down is keyed
  // by (sent_at, title) rather than an id, and the dialog shows the full
  // message the table had to truncate.
  const [open, setOpen] = useState<SentNotification | null>(null);
  const [recipPage, setRecipPage] = useState(1);

  const { data, isFetching } = useQuery({
    queryKey: ["admin", "notifications-sent", { q: qDebounced, source, days, page }],
    queryFn: () =>
      NotificationsAPI.sent({
        page,
        page_size: PAGE_SIZE,
        q: qDebounced || undefined,
        source: source || undefined,
        days: days ? Number(days) : undefined,
      }),
    enabled: allowed,
    refetchOnWindowFocus: false,
  });

  const { data: recip, isFetching: recipFetching } = useQuery({
    queryKey: [
      "admin",
      "notifications-sent-recipients",
      open?.sent_at,
      open?.title,
      open?.level,
      open?.sender_id,
      recipPage,
    ],
    queryFn: () =>
      NotificationsAPI.sentRecipients({
        sent_at: open!.sent_at,
        title: open!.title,
        // `/sent` groups on six fields; keying the drill-down on two let
        // two distinct same-second sends share one recipient list.
        level: open!.level || undefined,
        sender_id: open!.sender_id || undefined,
        page: recipPage,
        page_size: RECIPIENTS_PAGE_SIZE,
      }),
    enabled: open !== null,
    refetchOnWindowFocus: false,
  });

  function openSend(row: SentNotification) {
    setRecipPage(1);
    setOpen(row);
  }

  // The nav item is already gated, but a typed URL isn't.
  if (!allowed) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center text-sm text-muted-foreground">
        You don&apos;t have the Users section, so you can&apos;t see what was
        sent to users. The super admin grants it per admin.
      </div>
    );
  }

  const meta = data?.meta;
  const total = meta?.total ?? 0;

  const columns: Column<SentNotification>[] = [
    {
      key: "sent_at",
      header: "When",
      render: (r) => (
        <span className="text-xs tabular-nums text-muted-foreground">
          {stampIST(r.sent_at)}
        </span>
      ),
    },
    {
      key: "title",
      header: "Notification",
      // Messages run to 1000 characters. The td is nowrap, so the width cap
      // plus `truncate` keeps every row one line high; the full text lives
      // in the tooltip and in the drill-down dialog.
      className: "max-w-[380px]",
      render: (r) => (
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <LevelBadge level={r.level} />
            <span className="truncate text-sm font-medium" title={r.title}>
              {r.title}
            </span>
          </div>
          <div className="truncate text-xs text-muted-foreground" title={r.message}>
            {r.message}
          </div>
        </div>
      ),
    },
    {
      key: "source",
      header: "Source",
      render: (r) => (
        <span className="text-xs text-muted-foreground">{sourceLabel(r.source)}</span>
      ),
    },
    {
      key: "sender",
      header: "Sent by",
      className: "max-w-[180px]",
      render: (r) =>
        r.sender_name ? (
          <span className="truncate text-xs" title={`${r.sender_name} ${r.sender_code ?? ""}`}>
            {r.sender_name}
            {r.sender_code && (
              <span className="ml-1 font-mono text-[10px] text-muted-foreground">
                {r.sender_code}
              </span>
            )}
          </span>
        ) : (
          // Chart lines and payment-details notices carry no sender id.
          <span className="text-xs text-muted-foreground">Automatic</span>
        ),
    },
    {
      key: "recipients",
      header: "Users",
      align: "right",
      render: (r) => (
        <span className="text-xs font-semibold tabular-nums">{r.recipients}</span>
      ),
    },
    {
      key: "read_count",
      header: "Read",
      align: "right",
      render: (r) => <ReadCount read={r.read_count} total={r.recipients} />,
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Notification history"
        description={`${total} send${total === 1 ? "" : "s"} ${scopeLabel} — tap a row to see who got it`}
        actions={
          <Link href="/send-notification">
            <Button variant="secondary" className="gap-2">
              <Send className="size-4" /> Send a notification
            </Button>
          </Link>
        }
      />

      <p className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
        Every notification that reached a user — the broadcasts an admin typed
        on{" "}
        <Link href="/send-notification" className="underline hover:text-foreground">
          Send Notification
        </Link>
        , plus the automatic ones (chart lines saved, payment details changed).
        One row per send; click it for the recipient list and who has read it.{" "}
        <span className="font-semibold">
          Notifications are deleted automatically after 90 days
        </span>
        , so nothing older than that can be shown here.
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
            placeholder="Search title / message"
            className="pl-9"
          />
        </div>
        <select
          value={source}
          onChange={(e) => {
            setPage(1);
            setSource(e.target.value);
          }}
          className="h-10 rounded-md border border-border bg-background px-3 text-sm"
        >
          {SOURCES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={days}
          onChange={(e) => {
            setPage(1);
            setDays(e.target.value);
          }}
          className="h-10 rounded-md border border-border bg-background px-3 text-sm"
        >
          {DAY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* Desktop table. Phones get the card list below — six columns with a
          1000-character message don't survive a 360 px viewport. */}
      <div className="hidden md:block">
        <DataTable
          columns={columns}
          rows={data?.items}
          keyExtractor={(r) => `${r.sent_at}|${r.title}`}
          loading={isFetching && !data}
          empty={`Nothing has been sent ${scopeLabel} in this window.`}
          onRowClick={openSend}
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
            {`Nothing has been sent ${scopeLabel} in this window.`}
          </div>
        )}
        {data?.items?.map((r) => (
          <button
            key={`${r.sent_at}|${r.title}`}
            type="button"
            onClick={() => openSend(r)}
            className="w-full rounded-xl border border-border bg-card p-3 text-left transition-colors hover:bg-muted/40"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 items-center gap-1.5">
                <LevelBadge level={r.level} />
                <span className="truncate text-sm font-semibold">{r.title}</span>
              </div>
              <span className="shrink-0 text-[10px] text-muted-foreground">
                {sourceLabel(r.source)}
              </span>
            </div>
            {/* Two lines, then clipped — the dialog has the whole thing. */}
            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{r.message}</p>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
              <span>{stampIST(r.sent_at)}</span>
              <span>{r.sender_name ?? "Automatic"}</span>
              <span className="font-semibold text-foreground">{r.recipients} users</span>
              <ReadCount read={r.read_count} total={r.recipients} />
            </div>
          </button>
        ))}
      </div>

      {total > 0 && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          onPageChange={setPage}
        />
      )}

      <Dialog open={open !== null} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 pr-6">
              {open && <LevelBadge level={open.level} />}
              <span className="truncate">{open?.title}</span>
            </DialogTitle>
          </DialogHeader>

          {open && (
            <div className="space-y-3">
              {/* The full message — the table row could only show a line of it. */}
              <p className="max-h-32 overflow-y-auto whitespace-pre-wrap rounded-md border border-border bg-muted/30 px-3 py-2 text-xs leading-relaxed">
                {open.message}
              </p>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span>{stampIST(open.sent_at)}</span>
                <span>{sourceLabel(open.source)}</span>
                <span>
                  {open.sender_name
                    ? `${open.sender_name}${open.sender_code ? ` · ${open.sender_code}` : ""}`
                    : "Automatic"}
                </span>
                {open.link && <span className="font-mono">{open.link}</span>}
                <ReadCount read={open.read_count} total={open.recipients} />
              </div>

              <div className="max-h-[45vh] overflow-y-auto rounded-lg border border-border">
                {recipFetching && !recip && (
                  <div className="p-6 text-center text-sm text-muted-foreground">
                    Loading…
                  </div>
                )}
                {recip?.items?.map((u: SentRecipient) => (
                  <div
                    key={u.user_id}
                    className="flex items-center justify-between gap-2 border-b border-border px-3 py-2 last:border-b-0"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      {/* No code means the account was deleted after the send.
                          The row stays — it WAS delivered — but there is no
                          user left to name. */}
                      {u.user_code ? (
                        <span className="rounded-md bg-primary/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-primary">
                          {u.user_code}
                        </span>
                      ) : (
                        <span className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] font-semibold text-muted-foreground">
                          Deleted account
                        </span>
                      )}
                      <span className="truncate text-sm">{u.full_name || "—"}</span>
                    </div>
                    {u.is_read ? (
                      <span
                        className="shrink-0 text-[10px] font-semibold text-emerald-500"
                        title={`Read ${stampIST(u.read_at)}`}
                      >
                        Read
                      </span>
                    ) : (
                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        Unread
                      </span>
                    )}
                  </div>
                ))}
                {!recipFetching && (recip?.items?.length ?? 0) === 0 && (
                  <div className="p-6 text-center text-sm text-muted-foreground">
                    No recipients found — this send may have passed the
                    90-day cutoff since the list was loaded.
                  </div>
                )}
              </div>

              {(recip?.meta?.total ?? 0) > RECIPIENTS_PAGE_SIZE && (
                <Pagination
                  page={recipPage}
                  pageSize={RECIPIENTS_PAGE_SIZE}
                  total={recip?.meta?.total ?? 0}
                  onPageChange={setRecipPage}
                />
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
