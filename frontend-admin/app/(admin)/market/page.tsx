"use client";

/**
 * Market status — what the trading gates currently believe.
 *
 * Every number here is computed server-side by the SAME helpers the risk
 * enforcer, the pending-order poller and the order validator call. Nothing is
 * re-derived in the browser, because a status page that can be wrong
 * independently of the platform is worse than no page: it reassures you about
 * a gate that is actually mis-set.
 *
 * The two close columns are deliberate. "Order entry" is the time the
 * validator stops accepting new orders; "Risk gate" is the time
 * `is_after_close` starts treating the session as over, which is what silences
 * the poller and the enforcer and fires the EOD rollover. For NSE/BSE they are
 * different on purpose (15:30 vs 16:00). For MCX they are the same. A single
 * "close" column is exactly what let those two drift apart unnoticed and shut
 * MCX order entry and risk enforcement early, every evening, in silence.
 */

import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { MarketAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusPill } from "@/components/common/StatusPill";
import { DataTable, type Column } from "@/components/common/DataTable";

export default function MarketStatusPage() {
  const { data, isFetching, refetch } = useQuery({
    queryKey: ["admin", "market", "status"],
    queryFn: () => MarketAPI.status(),
    // Fast enough to watch a session open or close in real time, slow enough
    // that leaving the tab open costs the backend almost nothing.
    refetchInterval: 10_000,
  });

  const segCols: Column<any>[] = [
    { key: "group", header: "Segment" },
    {
      key: "state",
      header: "State",
      render: (r) => (
        <div className="flex items-center gap-2">
          <StatusPill status={r.state} />
          {r.note && <span className="text-xs text-muted-foreground">{r.note}</span>}
        </div>
      ),
    },
    { key: "opens", header: "Opens", render: (r) => r.opens ?? "—" },
    {
      key: "order_entry_closes",
      header: "Order entry closes",
      render: (r) => r.order_entry_closes ?? "—",
    },
    {
      key: "risk_gate_closes",
      header: "Risk gate closes",
      render: (r) => r.risk_gate_closes ?? "—",
    },
    {
      key: "close_source",
      header: "Close from",
      render: (r) => <span className="text-xs text-muted-foreground">{r.close_source}</span>,
    },
    {
      key: "holiday",
      header: "Today",
      render: (r) =>
        r.holiday ? (
          <span className="text-xs">
            {r.holiday.description}
            {!r.holiday.full_day && r.holiday.open_time
              ? ` · special session ${r.holiday.open_time}–${r.holiday.close_time ?? "close"}`
              : ""}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Market status"
        description={
          data
            ? `IST ${data.weekday} ${data.now_ist}${data.is_weekend ? " · weekend" : ""}`
            : "Live session state, as the trading gates compute it"
        }
        actions={
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`size-4 ${isFetching ? "animate-spin" : ""}`} /> Refresh
          </Button>
        }
      />

      <DataTable
        columns={segCols}
        rows={data?.segments}
        keyExtractor={(r) => r.group}
        loading={isFetching && !data}
        maxHeight=""
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Price feeds</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(data?.feeds ?? []).map((f: any) => (
              <div key={f.name} className="flex items-start justify-between gap-3 text-sm">
                <div>
                  <div>{f.name}</div>
                  {f.last_error && (
                    <div className="text-xs text-destructive">{f.last_error}</div>
                  )}
                </div>
                <div className="shrink-0 text-right">
                  <StatusPill
                    status={
                      f.error
                        ? "REJECTED"
                        : f.configured === false
                          ? "CLOSED"
                          : f.connected
                            ? "ACTIVE"
                            : "REJECTED"
                    }
                  />
                  {f.subscribed != null && (
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {f.subscribed} subscribed
                    </div>
                  )}
                </div>
              </div>
            ))}
            {!data?.feeds?.length && (
              <p className="text-sm text-muted-foreground">No feed data.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Background loops</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {/* These loops run on ONE worker — whichever holds the lock — so a
                held lock with a live TTL is the only cross-worker proof that
                anything is driving them. `leader:feed` unheld means no ticks,
                no parked fills and no stop-outs anywhere on the platform. */}
            {(data?.leaders ?? []).map((l: any) => (
              <div key={l.key} className="flex items-start justify-between gap-3 text-sm">
                <div>
                  <div>{l.what}</div>
                  <div className="font-mono text-xs text-muted-foreground">{l.key}</div>
                </div>
                <div className="shrink-0 text-right">
                  {/* held === null means we could not find out, which calls for
                      a different reaction than "nothing is holding this" — so
                      it must not render as a red "down" pill. */}
                  <StatusPill
                    status={l.held == null ? "PENDING" : l.held ? "ACTIVE" : "REJECTED"}
                  />
                  {l.error ? (
                    <div className="mt-0.5 text-xs text-amber-400">{l.error}</div>
                  ) : (
                    l.ttl_sec != null && (
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        renews in {l.ttl_sec}s
                      </div>
                    )
                  )}
                </div>
              </div>
            ))}
            {!data?.leaders?.length && (
              <p className="text-sm text-muted-foreground">No lock data.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
