import type { Metadata } from "next";
import { ArrowRight, LineChart, Network, ScrollText, ShieldCheck } from "lucide-react";
import {
  MpButton,
  MpCard,
  MpContainer,
  MpHeading,
  MpPageHero,
  MpProse,
  MpSection,
  MpStatGrid,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "Futures & Options on NFO — Nifty, Bank Nifty & Stock F&O | SaudaSaacha",
  description:
    "Trade index and stock derivatives on the NSE F&O segment with a live option chain and transparent SPAN + Exposure margins. Weekly and monthly expiries.",
};

const STATS = [
  { label: "Segment", value: "NSE F&O" },
  { label: "F&O Contracts", value: "200+" },
  { label: "Weekly Expiry", value: "Every Week" },
  { label: "Margin", value: "SPAN + Exposure" },
];

const INSTRUMENTS: [string, string, string, string][] = [
  ["NIFTY (FUT/OPT)", "NFO", "75", "SPAN + Exposure"],
  ["BANKNIFTY (FUT/OPT)", "NFO", "30", "SPAN + Exposure"],
  ["FINNIFTY (FUT/OPT)", "NFO", "65", "SPAN + Exposure"],
  ["RELIANCE FUT", "NFO", "500", "SPAN + Exposure"],
  ["HDFCBANK FUT", "NFO", "550", "SPAN + Exposure"],
  ["INFY FUT", "NFO", "400", "SPAN + Exposure"],
];

const FEATURES = [
  {
    icon: ScrollText,
    title: "Futures & Options",
    body: "Trade index and single-stock futures and options across the NSE F&O segment from one streamlined platform.",
  },
  {
    icon: Network,
    title: "Live Option Chain",
    body: "Analyse strikes, open interest and Greeks with a real-time option chain across weekly and monthly expiries.",
  },
  {
    icon: ShieldCheck,
    title: "Transparent SPAN + Exposure",
    body: "Margins follow SEBI's SPAN + Exposure framework, so you always know the exact capital required to hold a position.",
  },
];

export default function FuturesOptionsPage() {
  return (
    <>
      <MpPageHero
        eyebrow="NSE F&O"
        title="Futures & Options on NFO"
        lead="Trade index and stock derivatives on the NSE F&O segment with a live option chain and transparent SPAN + Exposure margins."
      >
        <MpButton href="/register" size="lg">
          Start Trading Now
          <ArrowRight className="size-4" />
        </MpButton>
        <MpButton href="/register" variant="secondary" size="lg" className="border-mp-border text-mp-text">
          Open Demo Account
        </MpButton>
      </MpPageHero>

      {/* Quick stats */}
      <MpSection>
        <MpStatGrid items={STATS} />
      </MpSection>

      {/* Why trade F&O */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading
          eyebrow="Overview"
          title="Why trade F&O with SaudaSaacha?"
        />
        <MpProse className="mt-6">
          Trade Nifty 50, Bank Nifty and single-stock futures and options on the
          NSE Futures &amp; Options (NFO) segment. Use a live option chain and
          choose weekly or monthly expiries. Margins are calculated transparently
          using SEBI&apos;s SPAN + Exposure framework — just the real
          exchange-mandated margin you need to carry a position.
        </MpProse>
      </MpSection>

      {/* Top tradable instruments */}
      <MpSection>
        <MpHeading eyebrow="Contracts" title="Top tradable instruments" />
        <div className="mt-10 overflow-x-auto rounded-2xl border border-mp-border bg-mp-surface">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-mp-border text-xs uppercase tracking-wide text-mp-text-mut">
                <th className="px-5 py-4 font-medium">Symbol</th>
                <th className="px-5 py-4 font-medium">Exchange</th>
                <th className="px-5 py-4 font-medium">Lot Size</th>
                <th className="px-5 py-4 font-medium">Margin</th>
              </tr>
            </thead>
            <tbody>
              {INSTRUMENTS.map((row) => (
                <tr key={row[0]} className="border-b border-mp-border last:border-0">
                  <td className="px-5 py-4 font-semibold text-mp-text">{row[0]}</td>
                  <td className="mp-num px-5 py-4 text-mp-text-mut">{row[1]}</td>
                  <td className="mp-num px-5 py-4 text-mp-text-mut">{row[2]}</td>
                  <td className="px-5 py-4 text-mp-text-mut">{row[3]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs text-mp-text-mut">
          Lot sizes are indicative and revised periodically by the exchange.
          Check the latest contract specifications before you trade.
        </p>
      </MpSection>

      {/* Why trade with us */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading
          align="center"
          eyebrow="Why SaudaSaacha"
          title="Why trade F&O with us"
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <MpCard key={f.title} className="flex flex-col gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                <f.icon className="size-6" />
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {f.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{f.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Ready to start trading?
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            Open your Demat &amp; trading account today and invest across NSE, BSE
            &amp; MCX with SaudaSaacha.
          </p>
          <div className="mt-9 flex justify-center">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Open Account Now
              <ArrowRight className="size-4" />
            </MpButton>
          </div>
        </MpContainer>
      </section>
    </>
  );
}
