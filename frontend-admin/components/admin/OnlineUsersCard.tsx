"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Download, RefreshCw } from "lucide-react";
import { UsersAPI, type OnlineUser } from "@/lib/api";
import { Button } from "@/components/ui/button";

/** "3m 20s" — short enough to sit in a table cell. */
function since(epochSec: number | null | undefined): string {
  if (!epochSec) return "—";
  const secs = Math.max(0, Math.floor(Date.now() / 1000 - epochSec));
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ${secs % 60}s`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

function clockIST(epochSec: number | null | undefined): string {
  if (!epochSec) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
    .format(new Date(epochSec * 1000))
    .replace(",", "");
}

/**
 * Who has the app open right now.
 *
 * Distinct from the ACTIVE status in the table below: that is whether an
 * account is allowed to trade, this is whether someone is actually
 * there. A user drops off the list when their app stops checking in —
 * see `presence_service` for the window.
 */
export function OnlineUsersCard() {
  const [rows, setRows] = useState<OnlineUser[]>([]);
  const [ttl, setTtl] = useState(90);
  const [loading, setLoading] = useState(true);
  // Re-render on a timer so the "for" column counts up without refetching.
  const [, setTick] = useState(0);

  async function load() {
    try {
      const d = await UsersAPI.online();
      setRows(d.users || []);
      setTtl(d.ttl_sec || 90);
    } catch {
      /* leave the last list up rather than blanking the card */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const poll = setInterval(() => void load(), 20_000);
    const tick = setInterval(() => setTick((n) => n + 1), 1000);
    return () => {
      clearInterval(poll);
      clearInterval(tick);
    };
  }, []);

  const csv = useMemo(() => {
    const head = ["Code", "Name", "Role", "Status", "Online since (IST)", "Online for"];
    const body = rows.map((r) => [
      r.user_code,
      r.full_name,
      r.role,
      r.status,
      clockIST(r.online_since),
      since(r.online_since),
    ]);
    return [head, ...body]
      .map((cols) =>
        cols.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(","),
      )
      .join("\n");
  }, [rows]);

  function download() {
    if (rows.length === 0) {
      toast.error("Nobody is online to export");
      return;
    }
    // Snapshot the moment it was taken — "online now" means nothing
    // without knowing when "now" was.
    const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `online-users-${stamp}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="rounded-xl border border-border">
      <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500/60" />
          <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
        </span>
        <div className="flex-1">
          <div className="text-sm font-semibold">
            Online now
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              {loading ? "…" : `${rows.length} user${rows.length === 1 ? "" : "s"}`}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground">
            Users with the app open. Drops off after {ttl}s without a check-in —
            separate from the ACTIVE account status below.
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={() => void load()}>
          <RefreshCw className="size-4" />
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={download}>
          <Download className="mr-1.5 size-4" /> Download
        </Button>
      </div>

      {loading ? (
        <p className="px-4 py-6 text-center text-xs text-muted-foreground">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="px-4 py-6 text-center text-xs text-muted-foreground">
          Nobody has the app open right now.
        </p>
      ) : (
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Code</th>
                <th className="px-4 py-2 text-left font-medium">Name</th>
                <th className="px-4 py-2 text-left font-medium">Online since</th>
                <th className="px-4 py-2 text-right font-medium">For</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-border/40">
                  <td className="px-4 py-2 font-mono">{r.user_code}</td>
                  <td className="px-4 py-2">
                    {r.full_name}
                    {r.is_demo ? (
                      <span className="ml-2 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-500">
                        Demo
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-muted-foreground">
                    {clockIST(r.online_since)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {since(r.online_since)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
