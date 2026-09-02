import Link from "next/link";
import type { Metadata } from "next";
import {
  ArrowRight,
  BookOpen,
  Brain,
  Calculator,
  CandlestickChart,
  ChartSpline,
  ClipboardCheck,
  Clock,
  Compass,
  Flame,
  IndianRupee,
  Lightbulb,
  PieChart,
  Receipt,
  ScrollText,
  Sparkles,
  Star,
  TrendingUp,
  Waypoints,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Learn",
  description:
    "Free, plain-English explainers on Indian markets — F&O mechanics, options Greeks, margin maths, taxes and contract notes — written by traders for traders.",
};

const TRACKS = [
  {
    icon: Compass,
    name: "Beginner basics",
    blurb: "Start here if 'margin' and 'lot size' still feel fuzzy.",
    count: "12 lessons · 90 min",
    items: [
      "What actually happens when you press BUY",
      "Equity delivery vs intraday — and why STT differs",
      "How to read a contract note (line by line)",
      "Funds, margins, and the difference between 'available' and 'used'",
    ],
  },
  {
    icon: TrendingUp,
    name: "F&O mechanics",
    blurb: "Index + stock derivatives, the way SEBI defines them.",
    count: "18 lessons · 3 hrs",
    items: [
      "Futures: pricing, basis, roll-over cost",
      "Options primer: intrinsic vs time value, payoff diagrams",
      "Greek by Greek — Delta, Gamma, Theta, Vega, Rho",
      "Iron condor / bull call / calendar — when each makes sense",
    ],
  },
  {
    icon: Calculator,
    name: "Margin maths",
    blurb: "SPAN + exposure, hedge benefits, intraday vs overnight.",
    count: "9 lessons · 75 min",
    items: [
      "What SPAN actually models (and what it doesn't)",
      "Exposure margin and why it changes intraday",
      "Hedge benefit — buying a far-OTM option to free margin",
      "ELM and how it stacks on top",
    ],
  },
  {
    icon: Receipt,
    name: "Taxes & filings",
    blurb: "STCG, LTCG, intraday speculation, F&O business income.",
    count: "11 lessons · 2 hrs",
    items: [
      "STT, CTT, GST, stamp duty, SEBI fee — what each is for",
      "How to file F&O under 'business income' (and the audit threshold)",
      "Carrying forward losses for 8 years — the actual rule",
      "Crypto: Section 115BBH, 1% TDS, and what 194S means",
    ],
  },
  {
    icon: ChartSpline,
    name: "Chart reading",
    blurb: "Price action without the cult — what setups actually edge.",
    count: "14 lessons · 2.5 hrs",
    items: [
      "Support, resistance, and why you should mark from highs not closes",
      "Breakouts vs fakeouts — volume + structure check",
      "Indicators that survived backtest (RSI / EMA cross / ATR)",
      "Multi-timeframe alignment in under 10 minutes",
    ],
  },
  {
    icon: Brain,
    name: "Discipline & risk",
    blurb: "The part most courses skip — and most traders fail on.",
    count: "10 lessons · 100 min",
    items: [
      "Risking 1R per trade — and what R should actually be",
      "Reading your own P&L — win-rate vs expectancy",
      "Drawdown psychology — when to pause, when to size down",
      "Journaling that takes 90 seconds per trade",
    ],
  },
];

const ARTICLES = [
  {
    cat: "Options",
    title: "Why your ATM call lost money even though NIFTY went up",
    excerpt:
      "A 45-minute IV crush after the budget can wipe a positive Delta. We break down a real trade with the Greeks at entry and exit.",
    time: "8 min read",
  },
  {
    cat: "Taxes",
    title: "Filing F&O as business income — the 2026 checklist",
    excerpt:
      "Audit threshold, the new 44AD path, and the form-fields most CAs still get wrong.",
    time: "12 min read",
  },
  {
    cat: "Margin",
    title: "How SPAN actually computes index F&O margin",
    excerpt:
      "The 16 scenarios, the worst-case selection, and how hedging brings it down. Worked example on BANKNIFTY.",
    time: "10 min read",
  },
  {
    cat: "Risk",
    title: "What a 'stop out' really means in practice",
    excerpt:
      "Reading the risk-engine logs from a real margin shortfall and exactly which positions got squared first.",
    time: "7 min read",
  },
  {
    cat: "Crypto",
    title: "Crypto tax in India for active traders, with examples",
    excerpt:
      "30% flat, 1% TDS, no set-off — and the trades that don't qualify as VDA.",
    time: "9 min read",
  },
  {
    cat: "Charts",
    title: "Reading the option chain like a level-2 quote",
    excerpt:
      "OI + change in OI + IV across strikes can tell you where dealers think NIFTY is pinned by expiry.",
    time: "11 min read",
  },
];

const GLOSSARY = [
  { term: "STT",   def: "Securities Transaction Tax — levied on every equity / F&O trade. Equity delivery: 0.1% both sides. F&O futures: 0.02% on sell. Options: 0.1% on premium on sell." },
  { term: "SPAN",  def: "Standard Portfolio Analysis of Risk — the model exchanges use to compute initial margin for F&O." },
  { term: "VWAP",  def: "Volume-Weighted Average Price — the average traded price weighted by volume for a session. Used as a benchmark for institutional fills." },
  { term: "GTT",   def: "Good-Till-Triggered — a price-conditional order parked at the broker, fires when the trigger hits." },
  { term: "ELM",   def: "Extreme Loss Margin — an additional buffer over SPAN, levied by exchanges, varies by scrip volatility." },
  { term: "DPSP",  def: "Days Sales Per Share — fundamental metric for equity research. Not the same as DSO." },
  { term: "CTT",   def: "Commodities Transaction Tax — equivalent of STT for non-agri MCX contracts." },
  { term: "Lot",   def: "The minimum tradeable unit for F&O contracts. Set by the exchange and revised periodically — synced into our terminal daily." },
];

export default function LearnPage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-border">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-primary/8 via-background to-background" />
        <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 sm:py-24 lg:px-8">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary">
            <Lightbulb className="size-3" /> The Learn hub
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            Trade better.
            <br />
            <span className="mp-gradient-text">Understand what you're doing.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Free, plain-English explainers on Indian markets, written by people
            who actually trade them. No upselling a course at the end. No
            mystical "secrets". Just the mechanics — done well.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="max-w-2xl">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">Tracks</span>
          <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Pick a track. Finish in a weekend.</h2>
          <p className="mt-3 text-muted-foreground">
            Six guided tracks, each between 75 minutes and 3 hours. Read in any
            order — every lesson stands alone.
          </p>
        </div>

        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          {TRACKS.map((t) => {
            const Icon = t.icon;
            return (
              <div key={t.name} className="group rounded-2xl border border-border/40 bg-card/60 p-6 transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/10">
                <div className="flex items-start gap-4">
                  <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
                    <Icon className="size-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="text-lg font-bold tracking-tight">{t.name}</h3>
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="size-3" /> {t.count}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{t.blurb}</p>
                    <ul className="mt-4 space-y-1.5 text-sm">
                      {t.items.map((it) => (
                        <li key={it} className="flex items-start gap-2">
                          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                          <span className="text-foreground/80">{it}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="border-y border-border/40 bg-muted/20">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
          <div className="flex items-end justify-between">
            <div className="max-w-2xl">
              <span className="text-xs font-semibold uppercase tracking-wider text-primary">From the journal</span>
              <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Latest articles.</h2>
            </div>
            <Link href="#" className="hidden text-sm font-semibold text-primary hover:underline sm:inline-flex">
              Browse all →
            </Link>
          </div>

          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {ARTICLES.map((a) => (
              <article key={a.title} className="group flex h-full flex-col rounded-2xl border border-border bg-background p-6 transition-all hover:-translate-y-0.5 hover:border-primary/40">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 font-semibold text-primary">{a.cat}</span>
                  <span>{a.time}</span>
                </div>
                <h3 className="mt-3 text-base font-semibold leading-snug transition-colors group-hover:text-primary">
                  {a.title}
                </h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-muted-foreground">{a.excerpt}</p>
                <div className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-primary">
                  Read article <ArrowRight className="size-3" />
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8">
        <div className="max-w-2xl">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">Glossary</span>
          <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Eight terms that confuse most new traders.</h2>
          <p className="mt-3 text-muted-foreground">
            Bookmark this page — these come up in nearly every contract note,
            margin statement and tax filing you'll encounter.
          </p>
        </div>
        <dl className="mt-10 grid gap-4 sm:grid-cols-2">
          {GLOSSARY.map((g) => (
            <div key={g.term} className="rounded-2xl border border-border/40 bg-card/60 p-5">
              <dt className="flex items-center gap-2 text-sm font-bold text-primary">
                <BookOpen className="size-4" />
                {g.term}
              </dt>
              <dd className="mt-1.5 text-sm text-muted-foreground">{g.def}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="rounded-3xl border border-primary/20 bg-gradient-to-br from-primary/15 via-primary/5 to-background p-10 sm:p-14">
          <div className="grid items-center gap-8 lg:grid-cols-[1fr_auto]">
            <div className="max-w-2xl">
              <ScrollText className="size-10 text-primary" />
              <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Get one trading idea, every Friday.</h2>
              <p className="mt-3 text-muted-foreground">
                The Friday Tape — one chart, one setup, one lesson. No spam,
                no upsells, no NFT-of-the-week. Just a clean weekly read.
              </p>
            </div>
            <form className="flex w-full max-w-md gap-2">
              <input
                type="email"
                placeholder="you@email.com"
                className="h-11 flex-1 rounded-md border border-border bg-background px-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                type="submit"
                className="inline-flex h-11 items-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 hover:bg-primary/90"
              >
                Subscribe
              </button>
            </form>
          </div>
        </div>
      </section>
    </>
  );
}
