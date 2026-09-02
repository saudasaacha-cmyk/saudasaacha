import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Award,
  BarChart3,
  BookOpen,
  Briefcase,
  Building2,
  CalendarDays,
  Calculator,
  Check,
  Code2,
  Coins,
  Cpu,
  Eye,
  Gauge,
  Globe,
  GraduationCap,
  IndianRupee,
  Layers,
  LineChart,
  Lock,
  Monitor,
  Plus,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Video,
  Wallet,
} from "lucide-react";
import {
  MpButton,
  MpCard,
  MpContainer,
  MpEyebrow,
  MpHeading,
  MpSection,
  MpStatGrid,
} from "@/components/marketing/mp-ui";
import { Boxes } from "@/components/ui/background-boxes";
import { HeroVideo } from "@/components/marketing/HeroVideo";
import { Typewriter } from "@/components/ui/typewriter-text";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "SaudaSaacha — Trade Equity, F&O, Commodities & IPOs on NSE, BSE & MCX",
  description:
    "Institutional-grade execution and a transparent, modern platform for every Indian investor — across Equity, F&O, Commodities and IPOs on NSE, BSE & MCX.",
};

const INTRO_CARDS = [
  {
    icon: BarChart3,
    title: "Equity & F&O",
    body: "7000+ stocks and index/stock derivatives with a live option chain and advanced charts.",
  },
  {
    icon: Coins,
    title: "Commodities & IPO",
    body: "Trade MCX Gold, Silver & Crude, and apply to mainboard IPOs in seconds via UPI.",
  },
];

const STATS_TOP = [
  { value: "99.9%", label: "Platform Uptime" },
  { value: "50L+", label: "Investors Onboarded" },
  { value: "5000+", label: "Stocks on NSE & BSE" },
  { value: "5 min", label: "Open Account In" },
];

const WHY = [
  {
    icon: Layers,
    title: "Deep NSE & BSE Liquidity",
    body: "Trade Nifty 50, Bank Nifty and thousands of stocks with tight bid-ask spreads and reliable fills across the cash and F&O segments.",
  },
  {
    icon: Gauge,
    title: "Lightning-Fast Order Execution",
    body: "Our order management system is tuned for millisecond execution on Intraday and F&O, ideal for active traders and algo strategies.",
  },
  {
    icon: ShieldCheck,
    title: "Transparent & Simple",
    body: "A clean, honest platform with no hidden conditions. What you see before you place an order is exactly what you get.",
  },
  {
    icon: Wallet,
    title: "All Indian Markets, One Account",
    body: "Equity Delivery, Intraday, Futures & Options, Commodities on MCX, IPOs and Mutual Funds — all from a single demat and trading account.",
  },
  {
    icon: Cpu,
    title: "Advanced Trading Technology",
    body: "Professional charts, full option chain, GTT and basket orders, price alerts and API access for algo trading.",
  },
];

const MARKETS = [
  {
    slug: "equity",
    icon: BarChart3,
    title: "Equity",
    body: "Invest in 5,000+ stocks on NSE & BSE — Reliance, TCS, HDFC Bank, Infosys, SBI and more — across Delivery and Intraday segments.",
  },
  {
    slug: "fno",
    icon: LineChart,
    title: "Futures & Options",
    body: "Trade Nifty 50, Bank Nifty and stock F&O with a live option chain, strategy builder and SPAN + Exposure margin support.",
  },
  {
    slug: "commodities",
    icon: Coins,
    title: "Commodities (MCX)",
    body: "Trade Gold, Silver, Crude Oil, Natural Gas and Copper futures on MCX with transparent margins and contract details.",
  },
  {
    slug: "indices",
    icon: TrendingUp,
    title: "Indices",
    body: "Track and trade benchmark indices like Nifty 50, Bank Nifty, Sensex and Nifty Financial Services in real time.",
  },
  {
    slug: "ipo",
    icon: Building2,
    title: "IPO & Mutual Funds",
    body: "Apply to mainboard and SME IPOs via UPI and invest in direct mutual funds — all from one place.",
  },
];

const ACCOUNTS = [
  {
    tier: "Beginner",
    name: "Equity Investor",
    segments: "Equity & MF",
    focus: "Long-term investing",
    body: "Perfect for long-term investors building a portfolio of stocks, ETFs and mutual funds for steady wealth creation.",
    feats: ["Equity delivery & ETFs", "Direct mutual funds", "IPO via UPI", "Full platform access"],
    cta: "Open Account",
    href: "/register",
    featured: false,
  },
  {
    tier: "Popular",
    name: "Active Trader",
    segments: "Intraday & F&O",
    focus: "Fast execution",
    body: "Built for Intraday and F&O traders who need fast fills and a live option chain across NSE, BSE & MCX.",
    feats: ["Intraday & F&O", "MIS intraday margin", "Live option chain", "Priority execution"],
    cta: "Start Trading",
    href: "/register",
    featured: true,
  },
  {
    tier: "Advanced",
    name: "F&O Pro",
    segments: "Futures & Options",
    focus: "Strategy tools",
    body: "For experienced derivatives traders — advanced option strategy tools, basket orders and clear SPAN + Exposure margins.",
    feats: ["Option strategy builder", "Basket & GTT orders", "Advanced analytics", "Dedicated support"],
    cta: "Open F&O",
    href: "/register",
    featured: false,
  },
  {
    tier: "Exclusive",
    name: "HNI / Algo",
    segments: "All Segments",
    focus: "Dedicated desk",
    body: "For high-volume traders and algo desks — API access, a relationship manager and a priority dealing desk.",
    feats: ["Relationship manager", "Priority dealing desk", "API / algo access", "Custom solutions"],
    cta: "Contact Us",
    href: "/contact",
    featured: false,
  },
];

const PLATFORMS = [
  {
    icon: Globe,
    tag: "Browser-Based",
    name: "SaudaSaacha Web Terminal",
    body: "A browser-based trading terminal with no downloads. Access NSE, BSE & MCX instantly from any device with advanced charts and all order types.",
  },
  {
    icon: Smartphone,
    tag: "iOS & Android",
    name: "SaudaSaacha Mobile App",
    body: "Trade on the go with live market data, the full option chain, GTT orders, price alerts and instant UPI funding.",
  },
  {
    icon: Monitor,
    tag: "Pro Grade",
    name: "SaudaSaacha Desktop",
    body: "A professional-grade desktop platform for active traders — multi-chart layouts, basket orders, hotkeys and API / algo integration.",
  },
];

const PLATFORM_FEATURES = [
  "100+ Technical Indicators",
  "Multi-Chart Layout",
  "One-Click Trading",
  "Live Option Chain",
  "GTT & Basket Orders",
  "Price & Alert Notifications",
];

const CONDITIONS = [
  {
    icon: Globe,
    title: "Direct Exchange Execution",
    body: "Orders are placed straight to NSE, BSE & MCX with transparent, real-time fills — no opaque routing or manual intervention.",
  },
  {
    icon: ShieldCheck,
    title: "Transparent & Upfront",
    body: "No hidden conditions. Every applicable statutory levy is shown clearly before you place an order, so there are never any surprises.",
  },
  {
    icon: Gauge,
    title: "MIS & F&O Margins",
    body: "Get MIS intraday margins on eligible stocks and clear SPAN + Exposure margin requirements for Futures & Options. Trade responsibly.",
  },
  {
    icon: Lock,
    title: "Risk Management",
    body: "Stop Loss, Stop-Loss Market (SL-M), GTT triggers, square-off alerts and margin notifications are built into every account.",
  },
];

const RISK_TOOLS = [
  "Stop Loss & SL-M Orders",
  "GTT Triggers",
  "Square-off Alerts",
  "Margin Notifications",
];

const TOOLS = [
  { icon: LineChart, title: "Daily Market Analysis", body: "Expert daily views on Nifty, Bank Nifty & stocks" },
  { icon: BookOpen, title: "Equity Research Reports", body: "In-depth fundamental & technical reports" },
  { icon: TrendingUp, title: "Trade & Investment Ideas", body: "Actionable stock and F&O ideas" },
  { icon: Sparkles, title: "AI-Powered Stock Insights", body: "Machine-learning driven screeners" },
  { icon: CalendarDays, title: "Results & Events Calendar", body: "Track earnings, dividends & corporate actions" },
  { icon: Calculator, title: "Margin Calculator", body: "Know your margins before you trade" },
  { icon: Code2, title: "API & Algo Trading", body: "Build and deploy your own strategies" },
];

const CHART_TABS = ["Nifty 50", "Bank Nifty", "Sensex", "Reliance", "MCX Gold"];

const EDU_GUIDES = [
  { icon: BookOpen, title: "Stock Market Basics", body: "Understand equity, demat and how NSE & BSE work" },
  { icon: LineChart, title: "F&O & Options Strategies", body: "Learn derivatives and proven option strategies" },
  { icon: Video, title: "Video Tutorials", body: "Learn visually at your own pace" },
  { icon: Users, title: "Weekly Live Webinars", body: "Interactive sessions with market experts" },
  { icon: GraduationCap, title: "E-books & Market Manuals", body: "Comprehensive reference material" },
];

const PAYMENT_METHODS = [
  "UPI",
  "Net Banking",
  "NEFT / RTGS / IMPS",
  "Debit Card",
  "Bank Transfer",
  "Auto-Pay Mandate",
];

const PAYMENT_STATS = [
  { value: "0%", label: "Deposit Fees" },
  { value: "Instant", label: "Processing Time" },
  { value: "24/7", label: "Availability" },
];

const ABOUT_STATS = [
  { value: "50L+", label: "Investors onboarded", sub: "across 200+ cities" },
  { value: "99.9%", label: "Platform uptime", sub: "during market hours" },
  { value: "7000+", label: "Stocks & ETFs", sub: "on NSE & BSE" },
  { value: "10X", label: "Faster execution", sub: "direct exchange routing" },
];

const VALUES = [
  {
    icon: ShieldCheck,
    title: "Transparency",
    body: "We believe in fair trading conditions and clear, honest communication with no hidden surprises.",
  },
  {
    icon: Cpu,
    title: "Innovation",
    body: "We continuously improve our trading technology to deliver the best performance.",
  },
  {
    icon: Lock,
    title: "Integrity",
    body: "We operate with honesty, professionalism, and strong ethical standards.",
  },
];

const LONG_TERM = [
  "Equity delivery, ETFs & direct mutual funds",
  "Apply to IPOs directly via UPI",
  "GTT orders to invest at your target price",
  "Portfolio tracking and detailed reports",
  "100% online account opening",
];

const PARTNER_BENEFITS = [
  "Attractive partner rewards",
  "Lifetime recurring rewards",
  "Partner dashboard tracking",
  "Marketing support",
];

const PARTNER_TIERS = [
  { name: "Silver Partner", sub: "Starter tier" },
  { name: "Gold Partner", sub: "Growth tier" },
  { name: "Platinum Partner", sub: "Elite tier" },
];

const AWARDS = [
  { title: "Best Discount Broker", org: "India FinTech Awards", year: "2025" },
  { title: "Excellence in Trading Tech", org: "BFSI Innovation Summit", year: "2024" },
  { title: "Most Trusted Demat Platform", org: "Investor Choice Awards", year: "2024" },
];

const GET_STARTED = [
  { n: "1", title: "Open Demat Account", body: "Complete e-KYC with PAN & Aadhaar in minutes." },
  { n: "2", title: "Add Funds", body: "Add money instantly via UPI or Net Banking." },
  { n: "3", title: "Start Investing", body: "Trade Equity, F&O, Commodities, IPO & Mutual Funds." },
];

const FAQS = [
  {
    q: "How do I open a demat & trading account?",
    a: "Complete a 100% online e-KYC with your PAN and Aadhaar. Most accounts are ready to trade within minutes.",
  },
  {
    q: "What can I trade on SaudaSaacha?",
    a: "Equity Delivery and Intraday, Futures & Options, Commodities on MCX, IPOs and Mutual Funds — all from a single account.",
  },
  {
    q: "Are my securities and funds safe?",
    a: "Your securities are held in your own demat account with the depository, and funds move only through regulated banking channels.",
  },
  {
    q: "Which platforms can I trade on?",
    a: "A browser-based web terminal, iOS and Android apps, and a pro-grade desktop platform. Your account works seamlessly across all of them.",
  },
  {
    q: "Can I apply for IPOs and invest in mutual funds?",
    a: "Yes. Apply to mainboard and SME IPOs via UPI and invest in direct mutual funds, all from the same platform.",
  },
];


export default function HomePage() {
  return (
    <>
      {/* ── Hero (dark) — unchanged ───────────────────────────────── */}
      <section className="mp-dark relative flex min-h-screen items-center overflow-hidden bg-mp-bg text-mp-text">
        {/* Animated brand-green grid */}
        <Boxes />
        {/* Radial fade keeps the grid subtle and the headline readable.
            pointer-events-none is REQUIRED so hover reaches the <Boxes> grid
            underneath — otherwise this overlay swallows every mouse-move. */}
        <div
          className="pointer-events-none absolute inset-0 z-10 bg-mp-bg [mask-image:radial-gradient(transparent,white)]"
          aria-hidden
        />
        {/* Center green glow */}
        <div
          className="pointer-events-none absolute left-1/2 top-1/2 z-[1] h-[720px] w-[1100px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-mp-primary/25 blur-[170px]"
          aria-hidden
        />
        {/* pointer-events-none lets the grid behind stay hoverable; the CTA
            row re-enables pointer events for itself. */}
        <MpContainer className="pointer-events-none relative z-20 w-full py-20 sm:py-28">
          <div className="mx-auto flex max-w-6xl flex-col items-center text-center">
            <h1 className="mp-fade-up font-display text-4xl font-bold leading-[1.1] text-mp-text sm:text-5xl lg:text-[3.5rem] xl:text-6xl">
              <Typewriter
                text="Your trading edge deserves real capital."
                speed={55}
                cursor=""
              />
              <br />
              <span className="text-mp-primary-2">
                <Typewriter
                  text="Not your savings."
                  speed={55}
                  startDelay={2400}
                  cursor="|"
                />
              </span>
            </h1>
            <p className="mp-fade-up mp-fade-up-d1 mt-6 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
              Open a Demat account and trade Equity, F&O, Commodities and IPOs
              across NSE, BSE & MCX — institutional-grade execution and a
              transparent, modern platform.
            </p>
            <div className="mp-fade-up mp-fade-up-d2 pointer-events-auto mt-9 flex flex-col items-center gap-3 sm:flex-row">
              <MpButton href="/register" size="lg" className="w-full sm:w-auto">
                Open Account
                <ArrowRight className="size-4" />
              </MpButton>
              <MpButton
                href="#how-it-works"
                variant="secondary"
                size="lg"
                className="w-full border-mp-border text-mp-text hover:border-mp-primary/60 sm:w-auto"
              >
                See how it works
              </MpButton>
            </div>
          </div>
        </MpContainer>
      </section>

      {/* ── Product video ─────────────────────────────────────────── */}
      <MpSection>
        <HeroVideo src="/margin_video.mp4" poster="/thumbnail.png" />
      </MpSection>

      {/* ── Intro: Innovating for Indian markets ──────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="For crafting confident investing journeys"
          title="Innovating for Indian markets"
          lead="We bring institutional-grade execution and a transparent, modern platform to every investor — across Equity, F&O, Commodities and IPOs on NSE, BSE & MCX."
        />
        <div className="mx-auto mt-12 grid max-w-4xl gap-5 sm:grid-cols-2">
          {INTRO_CARDS.map((c) => (
            <MpCard key={c.title} className="flex flex-col gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                <c.icon className="size-6" />
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {c.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{c.body}</p>
            </MpCard>
          ))}
        </div>
        <p className="mx-auto mt-10 max-w-3xl text-center text-base leading-[1.7] text-mp-text-mut">
          For over a decade, we have helped Indian investors and active traders
          grow with confidence. Through technology, transparency and trust, we
          build a platform that performs when it matters — on every order and
          every settlement.
        </p>
      </MpSection>

      {/* ── Making a difference (stats) ───────────────────────────── */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading plain align="center" eyebrow="Making a difference" title="Numbers that speak" />
        <div className="mt-12">
          <MpStatGrid items={STATS_TOP} />
        </div>
      </MpSection>

      {/* ── Why Choose ────────────────────────────────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="Why Choose Us"
          title="Why Choose SaudaSaacha"
          lead="We combine advanced technology with trader-friendly pricing to give you the edge across NSE, BSE & MCX."
        />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {WHY.map((w) => (
            <MpCard key={w.title} className="flex flex-col gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                <w.icon className="size-6" />
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {w.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{w.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* ── Indian Markets Access ─────────────────────────────────── */}
      <MpSection id="markets" className="bg-mp-surface-2/60">
        <MpHeading plain
          align="center"
          eyebrow="Markets"
          title="Indian Markets Access"
          lead="Access NSE, BSE & MCX across Equity, F&O, Commodities, IPO and Mutual Funds from a single account."
        />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {MARKETS.map((m) => (
            <div key={m.title} id={`market-${m.slug}`} className="scroll-mt-28">
              <MpCard className="flex h-full flex-col gap-4">
                <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                  <m.icon className="size-6" />
                </span>
                <h3 className="font-display text-lg font-semibold text-mp-text">
                  {m.title}
                </h3>
                <p className="text-sm leading-[1.6] text-mp-text-mut">{m.body}</p>
              </MpCard>
            </div>
          ))}
          <MpCard className="flex flex-col items-start justify-center gap-3 border-dashed">
            <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
              <Plus className="size-6" />
            </span>
            <p className="text-sm leading-[1.6] text-mp-text-mut">
              And thousands more stocks &amp; contracts available across every
              segment.
            </p>
          </MpCard>
        </div>
        <div className="mt-10 flex justify-center">
          <MpButton href="/instruments" variant="secondary">
            Explore All Markets
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>

      {/* ── Account Types ─────────────────────────────────────────── */}
      <MpSection id="accounts">
        <MpHeading plain
          align="center"
          eyebrow="Accounts"
          title="Account Types"
          lead="Choose the account that matches your investing and trading style."
        />
        <div className="mt-12 grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {ACCOUNTS.map((a) => (
            <MpCard
              key={a.name}
              className={cn(
                "flex flex-col gap-4",
                a.featured && "ring-1 ring-mp-primary/40",
              )}
            >
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-mp-surface-2 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-mp-text-mut">
                  {a.tier}
                </span>
                {a.featured ? (
                  <span className="rounded-full bg-mp-primary/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-mp-primary">
                    Popular
                  </span>
                ) : null}
              </div>
              <h3 className="font-display text-xl font-bold text-mp-text">
                {a.name}
              </h3>
              <div className="flex flex-col gap-1 text-xs text-mp-text-mut">
                <span>
                  <span className="font-semibold text-mp-text">Segments:</span>{" "}
                  {a.segments}
                </span>
                <span>
                  <span className="font-semibold text-mp-text">Focus:</span>{" "}
                  {a.focus}
                </span>
              </div>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{a.body}</p>
              <ul className="flex flex-col gap-2">
                {a.feats.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-mp-text">
                    <Check className="size-4 shrink-0 text-mp-primary" />
                    {f}
                  </li>
                ))}
              </ul>
              <MpButton href={a.href} variant={a.featured ? "primary" : "secondary"} className="mt-auto">
                {a.cta}
              </MpButton>
            </MpCard>
          ))}
        </div>
        <div className="mt-10 flex justify-center">
          <MpButton href="/pricing" variant="secondary">
            Compare All Accounts
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>

      {/* ── Platform ──────────────────────────────────────────────── */}
      <MpSection id="platform" className="bg-mp-surface-2/60">
        <MpHeading plain
          align="center"
          eyebrow="Platform"
          title="Next-Generation Trading Platform"
          lead="A trading environment designed for performance and reliability."
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {PLATFORMS.map((p) => (
            <MpCard key={p.name} className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                  <p.icon className="size-6" />
                </span>
                <span className="rounded-full bg-mp-surface-2 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-mp-text-mut">
                  {p.tag}
                </span>
              </div>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {p.name}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{p.body}</p>
            </MpCard>
          ))}
        </div>
        <div className="mt-8 flex flex-wrap justify-center gap-2.5">
          {PLATFORM_FEATURES.map((f) => (
            <span
              key={f}
              className="rounded-full border border-mp-border bg-mp-surface px-4 py-2 text-xs font-medium text-mp-text"
            >
              {f}
            </span>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <MpButton href="/instruments">
            Explore Platform
            <ArrowRight className="size-4" />
          </MpButton>
          <MpButton href="/register" variant="secondary">
            Try Demo
          </MpButton>
        </div>
      </MpSection>

      {/* ── Trading Conditions ────────────────────────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="Trading Conditions"
          title="Professional Trading Conditions"
          lead="Direct NSE, BSE & MCX execution with transparent, upfront conditions and clear margin requirements on every trade."
        />
        <div className="mt-12 grid gap-5 sm:grid-cols-2">
          {CONDITIONS.map((c) => (
            <MpCard key={c.title} className="flex items-start gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                <c.icon className="size-5" />
              </span>
              <div>
                <h3 className="font-display text-base font-semibold text-mp-text">
                  {c.title}
                </h3>
                <p className="mt-1.5 text-sm leading-[1.6] text-mp-text-mut">
                  {c.body}
                </p>
              </div>
            </MpCard>
          ))}
        </div>
        <div className="mt-8 rounded-2xl border border-mp-border bg-mp-surface p-6">
          <h3 className="font-display text-base font-semibold text-mp-text">
            Built-in Risk Management Tools
          </h3>
          <div className="mt-4 flex flex-wrap gap-2.5">
            {RISK_TOOLS.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-2 rounded-full bg-mp-primary/10 px-4 py-2 text-xs font-medium text-mp-primary"
              >
                <Check className="size-3.5" />
                {t}
              </span>
            ))}
          </div>
        </div>
      </MpSection>

      {/* ── Tools & Research ──────────────────────────────────────── */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading plain
          align="center"
          eyebrow="Tools & Research"
          title="Professional Tools & Research"
          lead="Professional research and analytical tools to support informed investing on NSE, BSE & MCX."
        />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {TOOLS.map((t) => (
            <MpCard key={t.title} className="flex items-start gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                <t.icon className="size-5" />
              </span>
              <div>
                <h3 className="font-display text-base font-semibold text-mp-text">
                  {t.title}
                </h3>
                <p className="mt-1 text-sm leading-[1.5] text-mp-text-mut">
                  {t.body}
                </p>
              </div>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* ── Live Charts ───────────────────────────────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="Live Charts"
          title="Live Market Charts"
          lead="Real-time professional charts powered by the world's leading charting technology."
        />
        <div className="mt-10 flex flex-wrap justify-center gap-2.5">
          {CHART_TABS.map((t, i) => (
            <span
              key={t}
              className={cn(
                "rounded-full px-4 py-2 text-sm font-medium",
                i === 0
                  ? "bg-mp-primary text-white"
                  : "border border-mp-border text-mp-text-mut",
              )}
            >
              {t}
            </span>
          ))}
        </div>
        <div className="mx-auto mt-8 max-w-3xl rounded-2xl border border-mp-border bg-mp-surface p-8 text-center">
          <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
            <BarChart3 className="size-7" />
          </span>
          <h3 className="mt-5 font-display text-lg font-semibold text-mp-text">
            NIFTY 50
          </h3>
          <p className="mt-2 text-sm leading-[1.6] text-mp-text-mut">
            Interactive live charts for Nifty 50 with professional indicators,
            multiple timeframes, and real-time pricing are available inside the
            SaudaSaacha trading terminal.
          </p>
        </div>
      </MpSection>

      {/* ── Education Center ──────────────────────────────────────── */}
      <MpSection id="education" className="bg-mp-surface-2/60">
        <MpHeading plain
          align="center"
          eyebrow="Education Center"
          title="Education Center"
          lead="We believe educated traders perform better. Our learning center supports continuous growth at every level."
        />
        <div className="mt-12 grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <div className="flex flex-col gap-5 rounded-2xl border border-mp-border bg-mp-surface p-8">
            <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
              <GraduationCap className="size-6" />
            </span>
            <h3 className="font-display text-xl font-bold text-mp-text">
              Start Your Learning Journey
            </h3>
            <p className="text-sm leading-[1.6] text-mp-text-mut">
              Whether you are starting your journey or refining advanced
              strategies, our education hub supports continuous growth with
              structured courses, live sessions, and expert-curated content.
            </p>
            <div className="mt-auto flex flex-col gap-3 sm:flex-row">
              <MpButton href="/learn">Explore Education</MpButton>
              <MpButton href="/register" variant="secondary">
                Start Demo
              </MpButton>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {EDU_GUIDES.map((g) => (
              <MpCard key={g.title} className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                  <g.icon className="size-5" />
                </span>
                <div>
                  <h4 className="text-sm font-semibold text-mp-text">{g.title}</h4>
                  <p className="mt-1 text-xs leading-[1.5] text-mp-text-mut">
                    {g.body}
                  </p>
                </div>
              </MpCard>
            ))}
          </div>
        </div>
      </MpSection>

      {/* ── Payments ──────────────────────────────────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="Payments"
          title="Fast & Secure Payments"
          lead="Multiple payment methods available with fast, hassle-free processing."
        />
        <div className="mt-12 flex flex-wrap justify-center gap-2.5">
          {PAYMENT_METHODS.map((m) => (
            <span
              key={m}
              className="inline-flex items-center gap-2 rounded-full border border-mp-border bg-mp-surface px-4 py-2 text-sm font-medium text-mp-text"
            >
              <IndianRupee className="size-4 text-mp-primary" />
              {m}
            </span>
          ))}
        </div>
        <div className="mx-auto mt-10 max-w-3xl">
          <MpStatGrid items={PAYMENT_STATS} />
        </div>
      </MpSection>

      {/* ── About ─────────────────────────────────────────────────── */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading plain
          eyebrow="About SaudaSaacha"
          title="Built on precision & trust"
        />
        <div className="mt-8 grid gap-10 lg:grid-cols-[1.3fr_1fr]">
          <div className="flex flex-col gap-5">
            <p className="text-base leading-[1.7] text-mp-text-mut">
              SaudaSaacha was founded with a clear vision — to give every Indian
              investor access to a professional-grade trading platform with
              transparent, simple investing on NSE, BSE & MCX.
            </p>
            <p className="text-base leading-[1.7] text-mp-text-mut">
              As a SEBI-registered stock broker, we combine advanced technology
              with deep market access to deliver a seamless experience across
              Equity, F&O, Commodities, IPO and Mutual Funds.
            </p>
            <p className="text-base leading-[1.7] text-mp-text-mut">
              From first-time investors opening a demat account to professional
              F&O and algo traders, SaudaSaacha provides the tools, speed and
              reliability to trade Indian markets with confidence.
            </p>
            <div className="flex flex-wrap gap-2.5">
              {["Transparency", "Innovation", "Integrity"].map((v) => (
                <span
                  key={v}
                  className="rounded-full bg-mp-primary/10 px-4 py-2 text-xs font-semibold text-mp-primary"
                >
                  {v}
                </span>
              ))}
            </div>
            <div>
              <MpButton href="/about" variant="secondary">
                Learn More About Us
                <ArrowRight className="size-4" />
              </MpButton>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {ABOUT_STATS.map((s) => (
              <MpCard key={s.label} className="flex flex-col gap-1">
                <span className="mp-num font-display text-3xl font-bold text-mp-primary">
                  {s.value}
                </span>
                <span className="text-sm font-medium text-mp-text">{s.label}</span>
                <span className="text-xs text-mp-text-mut">{s.sub}</span>
              </MpCard>
            ))}
          </div>
        </div>
      </MpSection>

      {/* ── Vision, Mission & Values ──────────────────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="Our Foundation"
          title="Vision, Mission & Values"
          lead="The principles that guide everything we do."
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-2">
          <MpCard className="flex flex-col gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
              <Eye className="size-5" />
            </span>
            <h3 className="font-display text-lg font-semibold text-mp-text">
              Our Vision
            </h3>
            <p className="text-sm leading-[1.6] text-mp-text-mut">
              To become India&apos;s most trusted broker, giving every investor
              access to professional technology and fair, transparent market
              access.
            </p>
          </MpCard>
          <MpCard className="flex flex-col gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
              <Target className="size-5" />
            </span>
            <h3 className="font-display text-lg font-semibold text-mp-text">
              Our Mission
            </h3>
            <p className="text-sm leading-[1.6] text-mp-text-mut">
              To empower every Indian investor by delivering a transparent,
              reliable platform and innovative trading tools.
            </p>
          </MpCard>
        </div>
        <div className="mt-5 grid gap-5 sm:grid-cols-3">
          {VALUES.map((v) => (
            <MpCard key={v.title} className="flex flex-col gap-3">
              <span className="grid size-11 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                <v.icon className="size-5" />
              </span>
              <h3 className="font-display text-base font-semibold text-mp-text">
                {v.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{v.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* ── Built for Long-Term Investing ─────────────────────────── */}
      <MpSection className="bg-mp-surface-2/60">
        <div className="grid gap-10 rounded-2xl border border-mp-border bg-mp-surface p-8 sm:p-10 lg:grid-cols-2">
          <div>
            <MpEyebrow plain>Wealth Building</MpEyebrow>
            <h2 className="mt-4 font-display text-2xl font-bold text-mp-text sm:text-3xl">
              Built for Long-Term Investing
            </h2>
            <p className="mt-3 text-base leading-[1.7] text-mp-text-mut">
              A delivery-first account designed for investors building long-term
              wealth in Indian markets. SaudaSaacha helps you build a portfolio
              of quality stocks, ETFs and mutual funds for steady, compounding
              growth.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <MpButton href="/register">
                Invest for the Long Term
                <ArrowRight className="size-4" />
              </MpButton>
              <MpButton href="/register" variant="secondary">
                Open Account
              </MpButton>
            </div>
          </div>
          <ul className="flex flex-col justify-center gap-3">
            {LONG_TERM.map((f) => (
              <li key={f} className="flex items-center gap-3 text-sm text-mp-text">
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                  <Check className="size-3.5" />
                </span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      </MpSection>

      {/* ── Partner Program ───────────────────────────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="Partner Program"
          title="Authorised Partner Program"
          lead="Become an Authorised Person and grow your business by referring investors to SaudaSaacha."
        />
        <div className="mt-12 grid gap-8 lg:grid-cols-2">
          <div className="grid gap-4 sm:grid-cols-2">
            {PARTNER_BENEFITS.map((b) => (
              <MpCard key={b} className="flex items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                  <Briefcase className="size-5" />
                </span>
                <span className="text-sm font-medium text-mp-text">{b}</span>
              </MpCard>
            ))}
          </div>
          <div className="flex flex-col gap-4">
            {PARTNER_TIERS.map((t) => (
              <div
                key={t.name}
                className="flex items-center justify-between rounded-2xl border border-mp-border bg-mp-surface px-5 py-4"
              >
                <div>
                  <h3 className="font-display text-base font-semibold text-mp-text">
                    {t.name}
                  </h3>
                  <p className="text-xs text-mp-text-mut">{t.sub}</p>
                </div>
                <span className="text-sm font-medium text-mp-primary">
                  Brokerage revenue share
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-10 flex justify-center">
          <MpButton href="/contact">
            Become a Partner
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>

      {/* ── Awards ────────────────────────────────────────────────── */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading plain
          align="center"
          eyebrow="Awards"
          title="Recognised across the industry"
          lead="Recognised for transparent pricing, dependable technology and investor-first design."
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {AWARDS.map((a) => (
            <MpCard key={a.title} className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                  <Award className="size-5" />
                </span>
                <span className="mp-num text-sm font-semibold text-mp-text-mut">
                  {a.year}
                </span>
              </div>
              <h3 className="font-display text-base font-semibold text-mp-text">
                {a.title}
              </h3>
              <p className="text-sm text-mp-text-mut">{a.org}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* ── Get Started (anchor: how-it-works) ────────────────────── */}
      <MpSection id="how-it-works">
        <MpHeading plain
          align="center"
          eyebrow="Get Started"
          title="Start Trading in 3 Simple Steps"
          lead="Begin your investing journey on NSE, BSE & MCX with SaudaSaacha today."
        />
        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {GET_STARTED.map((s) => (
            <MpCard key={s.n} className="flex flex-col gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary text-lg font-bold text-white">
                {s.n}
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {s.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{s.body}</p>
            </MpCard>
          ))}
        </div>
        <div className="mt-10 flex justify-center">
          <MpButton href="/register" size="lg">
            Open Trading Account
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>

      {/* ── FAQ ───────────────────────────────────────────────────── */}
      <MpSection>
        <MpHeading plain
          align="center"
          eyebrow="FAQ"
          title="Frequently Asked Questions"
          lead="Find answers to the most common questions about trading with SaudaSaacha."
        />
        <div className="mx-auto mt-12 flex max-w-3xl flex-col gap-3">
          {FAQS.map((f, i) => (
            <details
              key={f.q}
              open={i === 0}
              className="group rounded-3xl bg-mp-primary/[0.06] px-6 py-5 transition-all duration-200 open:bg-mp-surface open:shadow-xl open:shadow-mp-primary/5 open:ring-1 open:ring-mp-border [&_summary::-webkit-details-marker]:hidden"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                <span className="font-display text-base font-semibold text-mp-text sm:text-lg">
                  {f.q}
                </span>
                <span className="grid size-10 shrink-0 place-items-center rounded-full bg-mp-surface text-mp-primary ring-1 ring-mp-border transition-colors duration-200 group-open:bg-mp-primary group-open:text-white group-open:ring-0">
                  <Plus className="size-4 transition-transform duration-200 group-open:rotate-45" />
                </span>
              </summary>
              <p className="mt-4 max-w-2xl text-sm leading-[1.7] text-mp-text-mut">
                {f.a}
              </p>
            </details>
          ))}
        </div>
      </MpSection>

      {/* ── Final CTA (dark) ──────────────────────────────────────── */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-mp-primary-2">
            Start Investing Today
          </span>
          <h2 className="mx-auto mt-4 max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Ready to Invest in Indian Markets?
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            Join lakhs of investors who trust SaudaSaacha for fast execution, a
            powerful platform and transparent, simple investing.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Open Free Demat Account
              <ArrowRight className="size-4" />
            </MpButton>
            <MpButton
              href="/instruments"
              variant="secondary"
              size="lg"
              className="w-full border-mp-border text-mp-text hover:border-mp-primary/60 sm:w-auto"
            >
              Explore the Platform
            </MpButton>
          </div>
        </MpContainer>
      </section>
    </>
  );
}
