import Link from "next/link";
import type { Metadata } from "next";
import {
  ArrowRight,
  Bitcoin,
  Building2,
  Clock,
  Coins,
  DollarSign,
  Flame,
  Gem,
  Globe2,
  IndianRupee,
  Landmark,
  LineChart,
  Sparkles,
  TrendingUp,
  Wheat,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Markets",
  description:
    "Every market segment live on SaudaSaacha — NSE, BSE, MCX, currency F&O, spot forex, crypto, ETFs and mutual funds. Hours, lot sizes, statutory charges.",
};

const SEGMENTS = [
  {
    icon: Landmark,
    name: "NSE Equity (Cash)",
    instruments: "All A-group + most B-group · 1,800+ scrips",
    hours: "Mon–Fri · 09:15 – 15:30 IST",
    lot: "1 share",
    brokerage: "₹0 delivery (CNC) · ₹20 / order intraday (MIS)",
    statutory: "STT 0.1% delivery, 0.025% intraday sell · Exchange + GST + SEBI + stamp",
  },
  {
    icon: Building2,
    name: "BSE Equity (Cash)",
    instruments: "All actively traded scrips · including SME",
    hours: "Mon–Fri · 09:15 – 15:30 IST",
    lot: "1 share",
    brokerage: "₹0 delivery · ₹20 / order intraday",
    statutory: "Same as NSE cash · auto-routed via best-price logic when both segments are open",
  },
  {
    icon: TrendingUp,
    name: "NSE F&O",
    instruments: "NIFTY, BANKNIFTY, FINNIFTY weekly + monthly · stock futures & options",
    hours: "Mon–Fri · 09:15 – 15:30 IST",
    lot: "Per SEBI lot-size circular (synced daily)",
    brokerage: "₹20 / order flat — both futures and options",
    statutory: "STT 0.02% on futures sell, 0.1% on options premium sell · Exchange + GST + SEBI + stamp",
  },
  {
    icon: TrendingUp,
    name: "BSE F&O",
    instruments: "SENSEX, BANKEX options · select stock futures",
    hours: "Mon–Fri · 09:15 – 15:30 IST",
    lot: "Per SEBI lot-size circular",
    brokerage: "₹20 / order flat",
    statutory: "Same structure as NSE F&O",
  },
  {
    icon: DollarSign,
    name: "Currency F&O (CDS)",
    instruments: "USD/INR · EUR/INR · GBP/INR · JPY/INR · cross-pairs",
    hours: "Mon–Fri · 09:00 – 17:00 IST",
    lot: "USDINR 1,000 base · others per exchange spec",
    brokerage: "₹20 / order flat",
    statutory: "Exchange + GST + SEBI + stamp (no STT on currency)",
  },
  {
    icon: Wheat,
    name: "MCX Commodity",
    instruments: "Gold, Silver, Crude Oil, Natural Gas, Copper, Zinc, Aluminium, Cotton, Mentha, Castor seed",
    hours: "Mon–Fri · 09:00 – 23:30 IST (agri 09:00–21:00)",
    lot: "Per MCX contract spec · synced daily",
    brokerage: "₹20 / order flat",
    statutory: "CTT on non-agri sell side · Exchange + GST + SEBI + stamp",
  },
  {
    icon: Globe2,
    name: "Spot Forex (24×5)",
    instruments: "EUR/USD · GBP/USD · USD/JPY · gold (XAU/USD) · silver (XAG/USD) · 30+ pairs",
    hours: "Mon 03:00 IST – Sat 03:00 IST",
    lot: "Micro lot (0.01) · standard lot 1.0",
    brokerage: "Built into spread · no per-order fee",
    statutory: "GST on broker spread share only",
  },
  {
    icon: Bitcoin,
    name: "Crypto (24×7)",
    instruments: "BTC, ETH, SOL, BNB, XRP, ADA, DOGE + 40 more · INR-settled",
    hours: "Always open · including Indian holidays",
    lot: "Min order ₹100 notional",
    brokerage: "0.10% per leg",
    statutory: "1% TDS as per Section 194S on sell side · 30% tax on net gain to be paid by you",
  },
  {
    icon: Gem,
    name: "Precious Metals",
    instruments: "Gold (XAU/USD spot) · Silver (XAG/USD spot) · MCX gold mini",
    hours: "Mon–Fri · 24×5 spot · MCX 09:00 – 23:30 IST",
    lot: "Micro lot 0.01 spot · MCX mini 100 g",
    brokerage: "Spread (spot) · ₹20 / order (MCX)",
    statutory: "GST on broker margin · CTT on MCX sell",
  },
  {
    icon: Flame,
    name: "Energy",
    instruments: "Brent Crude (spot) · WTI · Natural Gas (MCX + spot)",
    hours: "Mon–Fri · global; MCX 09:00 – 23:30 IST",
    lot: "Spot 0.01 · MCX per spec",
    brokerage: "Spread (spot) · ₹20 / order (MCX)",
    statutory: "GST + CTT (MCX sell)",
  },
  {
    icon: Coins,
    name: "ETF",
    instruments: "All NSE/BSE-listed ETFs — equity, debt, gold, international, smart-beta",
    hours: "Mon–Fri · 09:15 – 15:30 IST",
    lot: "1 unit",
    brokerage: "₹0 delivery · ₹20 / order intraday",
    statutory: "STT 0.001% delivery (lower than equity) + standard exchange charges",
  },
  {
    icon: LineChart,
    name: "Mutual Funds (Direct)",
    instruments: "All AMCs · equity, debt, hybrid, index, ELSS · direct plans only",
    hours: "Order before 15:00 IST for same-day NAV",
    lot: "Min as per scheme (typically ₹100 SIP, ₹500 lump sum)",
    brokerage: "₹0 — we earn nothing on direct MF",
    statutory: "Standard exit-load + capital-gains tax per scheme",
  },
];

const HOURS_BAND = [
  { name: "Equity / F&O", value: "09:15 – 15:30 IST" },
  { name: "Currency F&O",  value: "09:00 – 17:00 IST" },
  { name: "MCX Commodity", value: "09:00 – 23:30 IST" },
  { name: "Spot Forex",    value: "Mon 03:00 – Sat 03:00 IST" },
  { name: "Crypto",        value: "24×7, no holidays" },
  { name: "Mutual Funds",  value: "Cut-off 15:00 IST" },
];

export default function MarketsPage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-border">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-primary/8 via-background to-background" />
        <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 sm:py-24 lg:px-8">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary">
            <Sparkles className="size-3" /> 14+ live segments
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            Every market your strategy needs.
            <br />
            <span className="mp-gradient-text">One account, one terminal.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            NSE, BSE and MCX for the Indian rhythm. AllTick for global forex,
            crypto and energy. Switching segments is a click, not a re-login.
          </p>
        </div>
      </section>

      <section className="border-b border-border bg-muted/20">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border/70 sm:grid-cols-3 lg:grid-cols-6">
            {HOURS_BAND.map((h) => (
              <div key={h.name} className="bg-card p-4 text-center">
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{h.name}</div>
                <div className="mt-1 inline-flex items-center gap-1 text-sm font-semibold">
                  <Clock className="size-3.5 text-primary" />
                  {h.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="max-w-2xl">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">Every segment</span>
          <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Hours, lot sizes, brokerage and statutory — at a glance.</h2>
          <p className="mt-3 text-muted-foreground">
            Click into any segment from the terminal to see the live contract spec, margin formula and current open interest.
          </p>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {SEGMENTS.map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.name} className="rounded-2xl border border-border/40 bg-card/60 p-6">
                <div className="flex items-start gap-4">
                  <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="size-6" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-lg font-bold tracking-tight">{s.name}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{s.instruments}</p>
                  </div>
                </div>
                <dl className="mt-5 grid gap-3 text-xs sm:grid-cols-2">
                  <div className="rounded-lg border border-border bg-background/60 p-3">
                    <dt className="font-semibold uppercase tracking-wider text-muted-foreground">Hours</dt>
                    <dd className="mt-1 font-medium">{s.hours}</dd>
                  </div>
                  <div className="rounded-lg border border-border bg-background/60 p-3">
                    <dt className="font-semibold uppercase tracking-wider text-muted-foreground">Lot</dt>
                    <dd className="mt-1 font-medium">{s.lot}</dd>
                  </div>
                  <div className="rounded-lg border border-border bg-background/60 p-3 sm:col-span-2">
                    <dt className="font-semibold uppercase tracking-wider text-muted-foreground">Brokerage</dt>
                    <dd className="mt-1 font-medium text-primary">{s.brokerage}</dd>
                  </div>
                  <div className="rounded-lg border border-border bg-background/60 p-3 sm:col-span-2">
                    <dt className="font-semibold uppercase tracking-wider text-muted-foreground">Statutory</dt>
                    <dd className="mt-1 text-muted-foreground">{s.statutory}</dd>
                  </div>
                </dl>
              </div>
            );
          })}
        </div>
      </section>

      <section className="border-y border-border/40 bg-card/40">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <div className="grid items-start gap-12 lg:grid-cols-2">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-primary">Indian holiday calendar</span>
              <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">We follow the NSE and MCX calendars to the day.</h2>
              <p className="mt-4 text-muted-foreground">
                Indian segments respect every gazetted exchange holiday. The
                holiday list is seeded into the platform on day one and updated
                quarterly as NSE / BSE / MCX publish their circulars.
              </p>
              <p className="mt-3 text-muted-foreground">
                On muhurat trading day (Diwali), the platform opens for the
                official 60-minute window. Crypto and global spot keep running
                — same as every other day.
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-background p-6">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <IndianRupee className="size-4 text-primary" />
                Indian segments on a typical Diwali day
              </div>
              <ul className="mt-4 space-y-2 text-sm">
                {[
                  ["Equity (NSE / BSE)",  "Muhurat 18:00 – 19:00 IST"],
                  ["NSE F&O",             "Muhurat session only"],
                  ["MCX",                 "Evening session normal"],
                  ["Currency F&O",        "Closed full day"],
                  ["Crypto",              "24×7 — always on"],
                ].map(([k, v]) => (
                  <li key={k} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                    <span className="text-muted-foreground">{k}</span>
                    <span className="font-medium">{v}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-[11px] text-muted-foreground">
                Exact muhurat timings are published by NSE 7 days in advance and pushed to the app via notification.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="rounded-3xl border border-primary/20 bg-gradient-to-br from-primary/15 via-primary/5 to-background p-10 text-center sm:p-14">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">One account, every market that matters.</h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Switch from NIFTY to BTC to gold without logging out. Margins,
            P&amp;L and ledger update in one place.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/register" className="inline-flex h-12 items-center gap-2 rounded-full bg-primary px-7 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90">
              Open account <ArrowRight className="size-4" />
            </Link>
            <Link href="/pricing" className="inline-flex h-12 items-center gap-2 rounded-full border border-border/60 bg-background px-7 text-sm font-semibold hover:bg-muted/50">
              See pricing
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
