import type { Metadata } from "next";
import { ArrowRight, Check } from "lucide-react";
import {
  MpButton,
  MpCard,
  MpContainer,
  MpHeading,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "Index Options — Trade NIFTY, BANKNIFTY & SENSEX | SaudaSaacha",
  description:
    "Trade NIFTY, BANKNIFTY and SENSEX index options on NSE & BSE with a live option chain, weekly and monthly expiries, and transparent SPAN + Exposure margins.",
};

const INSTRUMENTS = [
  {
    name: "NIFTY 50",
    exchange: "NSE · Index Options",
    desc: "India's benchmark index, tracking the 50 largest companies listed on the NSE. It's the most liquid, most widely traded index derivative in the country — which makes it ideal for clean intraday scalping and structured swing setups alike.",
    lot: "65 units",
  },
  {
    name: "BANKNIFTY",
    exchange: "NSE · Index Options",
    desc: "Tracks the 12 most liquid, large-cap banking stocks on the NSE. Known for higher volatility and wider intraday ranges — the favourite of experienced traders who thrive on momentum and can stomach the swings.",
    lot: "35 units",
  },
  {
    name: "SENSEX",
    exchange: "BSE · Index Options",
    desc: "India's oldest index, representing 30 well-established companies on the BSE. Its smaller lot size makes it the friendliest of the three for traders who prefer tighter risk control and smaller position sizes.",
    lot: "20 units",
  },
];

const CROSS_RULES = [
  "Options buying and selling are both supported on every index.",
  "Live NSE & BSE prices with a real-time option chain.",
  "Weekly and monthly expiries available across all three indices.",
  "Transparent SPAN + Exposure margins, shown before you trade.",
  "Trade from the web terminal, mobile app and desktop platform.",
  "Available on market days — no weekends or exchange holidays.",
];

export default function InstrumentsPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Index Options"
        title="Trade India's top indices."
        lead="NIFTY, BANKNIFTY and SENSEX index options on NSE & BSE — the three index derivatives that move the market every day, with a live option chain and weekly and monthly expiries."
      >
        <MpButton href="/register" size="lg">
          Open Account
          <ArrowRight className="size-4" />
        </MpButton>
      </MpPageHero>

      {/* Instrument cards */}
      <MpSection>
        <div className="flex flex-col gap-5">
          {INSTRUMENTS.map((ins) => (
            <MpCard key={ins.name} className="flex flex-col gap-6 lg:flex-row lg:gap-10">
              <div className="lg:w-2/5">
                <h2 className="font-display text-2xl font-bold text-mp-text">
                  {ins.name}
                </h2>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-mp-primary">
                  {ins.exchange}
                </p>
                <p className="mt-4 text-base leading-[1.65] text-mp-text-mut">
                  {ins.desc}
                </p>
              </div>
              <dl className="flex flex-1 flex-col divide-y divide-mp-border rounded-xl border border-mp-border">
                <div className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <dt className="text-mp-text-mut">Lot Size</dt>
                  <dd className="mp-num font-semibold text-mp-text">{ins.lot}</dd>
                </div>
                <div className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <dt className="text-mp-text-mut">Trading Hours</dt>
                  <dd className="mp-num font-semibold text-mp-text">
                    9:15 AM – 3:30 PM IST
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <dt className="text-mp-text-mut">Segment</dt>
                  <dd className="text-right font-medium text-mp-primary">
                    Index Options (Buy & Sell)
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <dt className="text-mp-text-mut">Margin</dt>
                  <dd className="text-right font-medium text-mp-text-mut">
                    SPAN + Exposure
                  </dd>
                </div>
              </dl>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* Cross-instrument rules */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading
          eyebrow="Universal rules"
          title="Trading rules that apply across all instruments"
        />
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {CROSS_RULES.map((rule) => (
            <div key={rule} className="flex items-start gap-3">
              <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                <Check className="size-3.5" />
              </span>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{rule}</p>
            </div>
          ))}
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Ready to trade NIFTY &amp; BANKNIFTY?
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            Open your Demat &amp; trading account today and start trading index
            options on NSE &amp; BSE.
          </p>
          <div className="mt-9 flex justify-center">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Open Account
              <ArrowRight className="size-4" />
            </MpButton>
          </div>
        </MpContainer>
      </section>
    </>
  );
}
