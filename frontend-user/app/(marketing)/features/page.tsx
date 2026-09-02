import Link from "next/link";
import type { Metadata } from "next";
import {
  ArrowRight,
  Bell,
  CandlestickChart,
  CheckCircle2,
  ClipboardList,
  FileText,
  Gauge,
  LayoutDashboard,
  LineChart,
  Lock,
  PieChart,
  Receipt,
  ScanLine,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Timer,
  Wallet,
  Wifi,
  Workflow,
  Zap,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Features",
  description:
    "The pro terminal, mobile app, risk engine, ledger and contract-note system that power SaudaSaacha. Every feature, in detail.",
};

const HERO_PILLARS = [
  {
    icon: CandlestickChart,
    title: "The trading terminal",
    body: "One screen for chart, depth, ladder, orders and positions. Saves your layout per segment so you don't re-arrange between equity and options.",
  },
  {
    icon: ShieldCheck,
    title: "The risk engine",
    body: "Live margin, daily MTM, stop-out at 80% and exit-only at 90% — enforced automatically by a 5-second loop. Sleep through the next gap-down.",
  },
  {
    icon: Receipt,
    title: "The ledger",
    body: "Double-entry, append-only, reconciled hourly. Every paisa traceable from UPI deposit to expiry settlement to withdrawal.",
  },
];

const TERMINAL = [
  { icon: LineChart,        title: "TradingView charts",      body: "Full Advanced Charts: 100+ indicators, multi-timeframe, draw tools, save templates per instrument." },
  { icon: ScanLine,         title: "Market depth (Level 2)",  body: "5 bids × 5 asks, total quantity, exchange-published spread. Updates with every tick." },
  { icon: ClipboardList,    title: "Order ladder",            body: "Click-to-trade on the bid or ask. Modify by drag. Cancel-all keyboard shortcut for risk-off." },
  { icon: PieChart,         title: "Option chain",            body: "Live OI, change in OI, IV per strike, ATM highlight. Filter strikes by ATM ± N or by moneyness." },
  { icon: Workflow,         title: "Basket orders",           body: "Stage multi-leg strategies as one click — bull call, iron condor, calendar — with computed margin shown before send." },
  { icon: Timer,            title: "GTT & SL-M & SL-L",       body: "Good-Till-Triggered orders parked in our matching engine, not at the exchange. Survive restarts; cancel from any device." },
];

const RISK = [
  { icon: Gauge,        title: "Live span + exposure",   body: "Margin recomputed every 5 s using SEBI's SPAN file. Pre-trade check stops orders you can't fund." },
  { icon: ShieldCheck,  title: "Stop-out + exit-only",   body: "At 80% margin used, only exit orders accepted. At 90%, system auto-squares off in FIFO order to bring you back under 70%." },
  { icon: Lock,         title: "Hold-time guards",       body: "Lock minimum holding to defeat fat-finger flipping. Optional cool-down between identical orders." },
  { icon: Wallet,       title: "Daily MTM enforcement",  body: "End-of-day MTM debit, F&O margin sweep, span re-evaluation against next-day requirement." },
];

const REPORTS = [
  { icon: FileText,    title: "Contract notes",   body: "ECN per trading day. STT, exchange, SEBI, GST and stamp duty itemised — exactly as SEBI prescribes." },
  { icon: Receipt,     title: "Tax P&L",          body: "Year-wise STCG, LTCG and intraday speculation split. CSV + PDF, ready for your CA." },
  { icon: LineChart,   title: "Trade book",       body: "Every fill across every segment, searchable by instrument, side, date range or order-id." },
  { icon: PieChart,    title: "P&L analytics",    body: "Win-rate, average R, max drawdown, time-of-day heatmap. Stop guessing what works." },
  { icon: Wallet,      title: "Ledger view",      body: "Running balance with every credit and debit — deposits, brokerage, statutory, expiry settlement, withdrawals." },
  { icon: Wallet,      title: "Brokerage report", body: "Per-segment, per-month brokerage with order count. No mystery 'maintenance' lines." },
];

const MOBILE = [
  { icon: Smartphone,   title: "Native-feel app",     body: "Bottom-nav, swipe gestures, biometric login. Identical positions, P&L and orders as desktop — same account, same speed." },
  { icon: Bell,         title: "Push price alerts",   body: "Set per-instrument alerts on price, % move, or option Greek. Delivered via push + WS in under 1 second." },
  { icon: Wifi,         title: "Offline-resilient",   body: "Token cache lets you check positions even on a flaky train Wi-Fi. Re-sync on reconnect." },
  { icon: LayoutDashboard, title: "One-click orders", body: "Quick-trade bar on the watchlist. Two taps from idea to order placed — including SL." },
];

const PLATFORM = [
  { title: "9 ms median order latency",      body: "p99 stays under 28 ms during peak NIFTY hours. Real numbers — published, not promised." },
  { title: "99.97% uptime over 6 months",    body: "Public status page at status.sachchasauda.com. Every incident has a public post-mortem." },
  { title: "256-bit TLS end-to-end",         body: "HSTS preload, cert pinning on mobile, no plain-HTTP listener anywhere in production." },
  { title: "ap-south-1 primary, Singapore DR", body: "India-resident data in AWS Mumbai. Singapore replica for global feeds. Failover tested quarterly." },
  { title: "Mandatory 2FA for admin paths",  body: "Every internal action is JWT + IP allowlist + TOTP. No engineer logs into the matching engine alone." },
  { title: "Append-only audit log",          body: "Every order, every settings change, every login is logged. Retained 1 year, signed." },
];

export default function FeaturesPage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-border">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-primary/8 via-background to-background" />
        <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 sm:py-24 lg:px-8">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary">
            <Sparkles className="size-3" /> The platform
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            A real platform.
            <br />
            <span className="mp-gradient-text">Not a thin app on a feed.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Three things make a broker: how it places your order, how it
            protects your capital, and how it accounts for your money. We built
            all three ground-up — and we're going to walk you through every
            piece.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="grid gap-5 lg:grid-cols-3">
          {HERO_PILLARS.map((p) => {
            const Icon = p.icon;
            return (
              <div key={p.title} className="rounded-2xl border border-border/40 bg-card/60 p-7">
                <div className="grid size-12 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
                  <Icon className="size-6" />
                </div>
                <h2 className="mt-5 text-lg font-bold tracking-tight">{p.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="border-y border-border/40 bg-muted/20">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <div className="max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">The terminal</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Six tools, one screen, zero tab-switching.</h2>
            <p className="mt-3 text-muted-foreground">
              Designed for traders who keep both screens busy. Saves layouts per segment so options-day and intraday-day don't fight each other.
            </p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {TERMINAL.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="rounded-2xl border border-border/40 bg-card/60 p-6">
                  <div className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="size-5" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold">{f.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">The risk engine</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">A safety net that actually catches you.</h2>
            <p className="mt-4 text-muted-foreground">
              Most brokers run risk checks once a minute. We run them every 5
              seconds — and we publish the formulas. There is no surprise
              square-off. There is no surprise margin call.
            </p>
            <ul className="mt-6 space-y-2 text-sm">
              {[
                "Live SPAN + exposure margin, computed against your real positions.",
                "Pre-trade check rejects orders you can't fund — no half-fills.",
                "80% margin used → exit-only mode (no new entries).",
                "90% margin used → auto-squareoff in FIFO order, back under 70%.",
                "All risk actions audit-logged and visible in your ledger.",
              ].map((t) => (
                <li key={t} className="flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-buy" />
                  <span className="text-muted-foreground">{t}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {RISK.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="rounded-2xl border border-border/40 bg-card/60 p-5">
                  <div className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="size-5" />
                  </div>
                  <h3 className="mt-3 text-sm font-semibold">{f.title}</h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{f.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-y border-border/40 bg-card/40">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <div className="max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">Reports &amp; books</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Every number, downloadable, in the format your CA expects.</h2>
            <p className="mt-3 text-muted-foreground">
              Contract notes, tax P&amp;L, ledger, trade book — generated nightly, signed and available as PDF + CSV.
            </p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {REPORTS.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="rounded-2xl border border-border bg-background p-6">
                  <div className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="size-5" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold">{f.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div className="grid gap-4 sm:grid-cols-2">
            {MOBILE.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="rounded-2xl border border-border/40 bg-card/60 p-5">
                  <div className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="size-5" />
                  </div>
                  <h3 className="mt-3 text-sm font-semibold">{f.title}</h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{f.body}</p>
                </div>
              );
            })}
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">Mobile</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Phone-first, not phone-last.</h2>
            <p className="mt-4 text-muted-foreground">
              The mobile app is built first, then ported up. Bottom-nav,
              biometric login, real haptics on order confirms. Available on
              iOS and Android — and identical to your desktop terminal under
              the hood.
            </p>
          </div>
        </div>
      </section>

      <section className="border-y border-border/40 bg-muted/20">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <div className="max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">Platform</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">The boring infrastructure, done unboringly well.</h2>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {PLATFORM.map((f) => (
              <div key={f.title} className="rounded-2xl border border-border bg-background p-6">
                <div className="flex items-start gap-3">
                  <Zap className="mt-0.5 size-5 shrink-0 text-primary" />
                  <div>
                    <div className="text-sm font-semibold">{f.title}</div>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{f.body}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="rounded-3xl border border-primary/20 bg-gradient-to-br from-primary/15 via-primary/5 to-background p-10 text-center sm:p-14">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">See it on your screen.</h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Open a free account, fund ₹100, place a token order on the smallest
            NSE lot. The fastest way to evaluate a broker is to actually trade
            on it.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/register" className="inline-flex h-12 items-center gap-2 rounded-full bg-primary px-7 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90">
              Open free account <ArrowRight className="size-4" />
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
