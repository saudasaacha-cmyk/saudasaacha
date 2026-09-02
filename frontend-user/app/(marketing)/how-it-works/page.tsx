import type { Metadata } from "next";
import { ArrowRight, BarChart3, Check, IndianRupee, ScrollText, Wallet } from "lucide-react";
import {
  MpButton,
  MpCard,
  MpContainer,
  MpHeading,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "How SaudaSaacha Works — Open an Account & Start Investing in 4 Steps",
  description:
    "Open a Demat & trading account, add funds, pick your market and place your trade. Start investing across NSE, BSE & MCX with SaudaSaacha in minutes.",
};

const STEPS = [
  {
    icon: ScrollText,
    n: "01",
    title: "Open your Demat account",
    body: "Complete a 100% online e-KYC with your PAN and Aadhaar. Most accounts are ready to trade within minutes — no paperwork, no branch visit.",
  },
  {
    icon: IndianRupee,
    n: "02",
    title: "Add funds",
    body: "Add money instantly via UPI or Net Banking. Your funds move only through regulated banking channels, and there are no deposit fees from our side.",
  },
  {
    icon: BarChart3,
    n: "03",
    title: "Pick your market",
    body: "Choose from Equity, Futures & Options, Commodities on MCX, IPOs and Mutual Funds — all from one account, with a live option chain and advanced charts.",
  },
  {
    icon: Wallet,
    n: "04",
    title: "Place your trade",
    body: "Place delivery, intraday, F&O and commodity orders with one-click execution, GTT and basket orders, and built-in risk tools like Stop Loss and SL-M.",
  },
];

const HIGHLIGHTS = [
  "100% online account opening with PAN & Aadhaar",
  "Instant UPI funding, no deposit fees",
  "Equity, F&O, Commodities, IPO & Mutual Funds in one account",
  "Live option chain, advanced charts and GTT orders",
  "Securities held safely in your own demat account",
  "Support in English and Hindi during IST hours",
];

export default function HowItWorksPage() {
  return (
    <>
      <MpPageHero
        eyebrow="How it works"
        title="From sign-up to your first trade, in four steps."
        lead="No complicated paperwork and nothing buried in fine print. Open an account, add funds, pick your market, and start investing across NSE, BSE & MCX."
      >
        <MpButton href="/register" size="lg">
          Open Account
          <ArrowRight className="size-4" />
        </MpButton>
        <MpButton href="/pricing" variant="secondary" size="lg" className="border-mp-border text-mp-text">
          See pricing
        </MpButton>
      </MpPageHero>

      {/* The four steps */}
      <MpSection>
        <MpHeading align="center" eyebrow="The four steps" title="The four steps" />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <MpCard key={s.n} className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                  <s.icon className="size-5" />
                </span>
                <span className="mp-num text-sm font-semibold text-mp-text-mut">
                  {s.n}
                </span>
              </div>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {s.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{s.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* What you get */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading
          align="center"
          eyebrow="What you get"
          title="Everything in one account"
          lead="One Demat & trading account covers every Indian market you want to trade."
        />
        <div className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-2">
          {HIGHLIGHTS.map((h) => (
            <div key={h} className="flex items-start gap-3">
              <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                <Check className="size-3.5" />
              </span>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{h}</p>
            </div>
          ))}
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Ready to get started?
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            Open your Demat &amp; trading account today and invest across NSE, BSE
            &amp; MCX with SaudaSaacha.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Open Account
              <ArrowRight className="size-4" />
            </MpButton>
            <MpButton
              href="/faq"
              variant="secondary"
              size="lg"
              className="w-full border-mp-border text-mp-text hover:border-mp-primary/60 sm:w-auto"
            >
              Read FAQs
            </MpButton>
          </div>
        </MpContainer>
      </section>
    </>
  );
}
