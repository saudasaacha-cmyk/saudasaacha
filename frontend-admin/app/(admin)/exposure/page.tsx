"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { TradingAPI } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { Card, CardContent } from "@/components/ui/card";
import { cn, formatINR } from "@/lib/utils";

type ExposureRow = {
  token: string;
  symbol: string;
  exchange: string;
  segment: string;
  net_qty: number;
  long_qty: number;
  short_qty: number;
  users: number;
  positions: number;
  notional: number;
  margin_used: number;
  ltp: number;
};

type ExposurePayload = {
  rows: ExposureRow[];
  totals: {
    symbols: number;
    positions: number;
    users: number;
    margin_used: number;
  };
};

const num = (v: number, dp = 2) =>
  Number(v ?? 0).toLocaleString("en-IN", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });

export default function ExposurePage() {
  const { data, isFetching } = useQuery<ExposurePayload>({
    queryKey: ["admin", "exposure"],
    queryFn: () => TradingAPI.exposure(),
    refetchInterval: 5000,
  });

  const rows = data?.rows ?? [];
  const totals = data?.totals;

  const columns: Column<ExposureRow>[] = [
    {
      key: "symbol",
      header: "Symbol",
      render: (r) => (
        <Link
          href={`/positions?q=${encodeURIComponent(r.symbol)}`}
          className="font-medium hover:underline"
        >
          {r.symbol}
        </Link>
      ),
    },
    { key: "exchange", header: "Exch" },
    {
      key: "side",
      header: "House side",
      // Clients net long ⇒ the house carries the opposite position.
      render: (r) => <HouseSide netQty={r.net_qty} />,
    },
    {
      key: "net_qty",
      header: "Client net qty",
      align: "right" as const,
      render: (r) => (
        <span
          className={cn(
            "font-tabular",
            r.net_qty > 0 ? "text-buy" : r.net_qty < 0 ? "text-sell" : "text-muted-foreground",
          )}
        >
          {num(r.net_qty, 2)}
        </span>
      ),
    },
    {
      key: "long_qty",
      header: "Long",
      align: "right" as const,
      render: (r) => <span className="font-tabular text-muted-foreground">{num(r.long_qty, 2)}</span>,
    },
    {
      key: "short_qty",
      header: "Short",
      align: "right" as const,
      render: (r) => <span className="font-tabular text-muted-foreground">{num(r.short_qty, 2)}</span>,
    },
    {
      key: "users",
      header: "Clients",
      align: "right" as const,
      render: (r) => <span className="font-tabular">{r.users}</span>,
    },
    {
      key: "positions",
      header: "Positions",
      align: "right" as const,
      render: (r) => <span className="font-tabular text-muted-foreground">{r.positions}</span>,
    },
    {
      key: "ltp",
      header: "Last price",
      align: "right" as const,
      render: (r) => (
        <span className="font-tabular">{r.ltp > 0 ? num(r.ltp, 2) : "—"}</span>
      ),
    },
    {
      key: "notional",
      header: "Notional",
      align: "right" as const,
      // Instrument's own currency (USD for CFDs, INR for MCX/NSE) — never summed.
      render: (r) => <span className="font-tabular">{num(r.notional, 0)}</span>,
    },
    {
      key: "margin_used",
      header: "Margin (₹)",
      align: "right" as const,
      render: (r) => <span className="font-tabular">{formatINR(r.margin_used)}</span>,
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Exposure"
        description="Every open client position folded together per symbol — the book the house is carrying. Refreshes every 5 seconds."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Symbols in book" value={String(totals?.symbols ?? 0)} />
        <Stat label="Open positions" value={String(totals?.positions ?? 0)} />
        <Stat label="Clients holding" value={String(totals?.users ?? 0)} />
        <Stat label="Margin used" value={formatINR(totals?.margin_used ?? 0)} />
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        keyExtractor={(r) => `${r.token}-${r.segment}`}
        loading={isFetching && !data}
        empty="No open positions right now."
        tableClassName="w-max"
      />

      <p className="text-xs text-muted-foreground">
        Notional is in each instrument&apos;s own currency (USD for CFDs, INR for
        Indian contracts), so it is shown per symbol and never added up. Margin is
        in rupees everywhere, so that column totals above.
      </p>
    </div>
  );
}

function HouseSide({ netQty }: { netQty: number }) {
  if (!netQty) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
        <Minus className="size-3" /> Flat
      </span>
    );
  }
  const houseShort = netQty > 0; // clients long ⇒ house short
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
        houseShort ? "bg-sell/10 text-sell" : "bg-buy/10 text-buy",
      )}
    >
      {houseShort ? <ArrowDownRight className="size-3" /> : <ArrowUpRight className="size-3" />}
      House {houseShort ? "short" : "long"}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
        <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
      </CardContent>
    </Card>
  );
}
