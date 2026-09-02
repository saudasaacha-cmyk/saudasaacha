import type { Metadata } from "next";
import { ArrowRight, BarChart3, Check, GraduationCap, RefreshCw } from "lucide-react";
import {
  MpButton,
  MpCard,
  MpContainer,
  MpHeading,
  MpPageHero,
  MpSection,
  MpStatGrid,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "Paper / Virtual Trading — Practice Risk-Free on NSE, BSE & MCX | SaudaSaacha",
  description:
    "Practise on live NSE, BSE & MCX prices with virtual funds — no real money, learn risk-free. No KYC required to start paper trading.",
};

const STATS = [
  { label: "Virtual Funds", value: "Included" },
  { label: "KYC", value: "Not Needed" },
  { label: "Duration", value: "Unlimited" },
  { label: "Platforms", value: "All" },
];

const FEATURES = [
  "Identical to the live trading environment",
  "Unlimited resets",
  "Trade Equity, F&O & Commodities",
  "No KYC or PAN required to start",
  "Live NSE, BSE & MCX prices",
  "Practice with virtual funds",
  "Test trading strategies risk-free",
  "Learn platform features",
];

const WHY = [
  {
    icon: GraduationCap,
    title: "Learn Risk-Free",
    body: "Practice strategies on Nifty, Bank Nifty, Reliance, TCS and more without risking real money.",
  },
  {
    icon: BarChart3,
    title: "Real Market Conditions",
    body: "Experience live NSE, BSE & MCX prices identical to a real trading account.",
  },
  {
    icon: RefreshCw,
    title: "Unlimited Resets",
    body: "Reset your virtual account anytime and start fresh with virtual funds.",
  },
];

const STEPS = [
  { n: "1", title: "Sign Up", body: "Create your paper trading account in seconds." },
  { n: "2", title: "Choose Segment", body: "Pick Equity, F&O or Commodities." },
  { n: "3", title: "Start Trading", body: "Practice with virtual funds." },
];

export default function DemoPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Paper / Virtual Trading"
        title="Practice risk-free with virtual funds"
        lead="Practise on live NSE, BSE & MCX prices with virtual funds — no real money, learn risk-free. No KYC required."
      >
        <MpButton href="/register" size="lg">
          Start Paper Trading Now
          <ArrowRight className="size-4" />
        </MpButton>
      </MpPageHero>

      {/* Quick stats */}
      <MpSection>
        <MpStatGrid items={STATS} />
      </MpSection>

      {/* Paper trading features */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading align="center" eyebrow="Features" title="Paper trading features" />
        <div className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <div key={f} className="flex items-center gap-3">
              <span className="grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                <Check className="size-3.5" />
              </span>
              <span className="text-sm text-mp-text">{f}</span>
            </div>
          ))}
        </div>
      </MpSection>

      {/* Why paper trading */}
      <MpSection>
        <MpHeading align="center" eyebrow="Why Paper Trading" title="Why use paper trading?" />
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
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

      {/* How to get started */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading align="center" eyebrow="Get Started" title="How to get started" />
        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {STEPS.map((s) => (
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
          <MpButton href="/register">
            Start Paper Trading
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Ready when you are
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            When you&apos;re confident with paper trading, open a live Demat +
            trading account and start investing for real.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Start Paper Trading
              <ArrowRight className="size-4" />
            </MpButton>
            <MpButton
              href="/#accounts"
              variant="secondary"
              size="lg"
              className="w-full border-mp-border text-mp-text hover:border-mp-primary/60 sm:w-auto"
            >
              View Live Accounts
            </MpButton>
          </div>
          <p className="mx-auto mt-10 max-w-3xl text-xs leading-relaxed text-mp-text-mut">
            Investments in securities market are subject to market risks. Read all
            the related documents carefully before investing.
          </p>
        </MpContainer>
      </section>
    </>
  );
}
