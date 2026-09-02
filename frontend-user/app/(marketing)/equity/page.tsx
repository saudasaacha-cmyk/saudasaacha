import type { Metadata } from "next";
import { ArrowRight, Clock, LineChart, Wallet } from "lucide-react";
import {
  MpButton,
  MpCard,
  MpContainer,
  MpHeading,
  MpPageHero,
  MpProse,
  MpSection,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "Equity — Invest in Stocks on NSE & BSE | SaudaSaacha",
  description:
    "Buy and sell shares of India's leading companies with lightning-fast execution. Equity delivery & intraday on NSE and BSE, T+1 settlement, 100% online.",
};

const STATS = [
  { value: "NSE / BSE", label: "Exchanges" },
  { value: "7000+", label: "Listed Stocks" },
  { value: "T+1", label: "Settlement" },
  { value: "100% Online", label: "Account Opening" },
];

const INSTRUMENTS = [
  { symbol: "RELIANCE", exchange: "NSE / BSE", lot: "1 share", margin: "Delivery & Intraday" },
  { symbol: "TCS", exchange: "NSE / BSE", lot: "1 share", margin: "Delivery & Intraday" },
  { symbol: "HDFCBANK", exchange: "NSE / BSE", lot: "1 share", margin: "Delivery & Intraday" },
  { symbol: "INFY", exchange: "NSE / BSE", lot: "1 share", margin: "Delivery & Intraday" },
  { symbol: "SBIN", exchange: "NSE / BSE", lot: "1 share", margin: "Delivery & Intraday" },
  { symbol: "ITC", exchange: "NSE / BSE", lot: "1 share", margin: "Delivery & Intraday" },
];

const FEATURES = [
  {
    icon: Wallet,
    title: "Delivery & Intraday",
    body: "Build a long-term portfolio with equity delivery, or trade actively with intraday positions — all on one platform.",
  },
  {
    icon: Clock,
    title: "Fast T+1 Settlement",
    body: "Shares and funds settle in your Demat account on a T+1 cycle, so your holdings are never locked up for long.",
  },
  {
    icon: LineChart,
    title: "Advanced Charts & Research",
    body: "Make informed decisions with TradingView-style charts, market depth, and live NSE & BSE data feeds.",
  },
];

export default function EquityPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Equity"
        title="Invest in Stocks on NSE & BSE"
        lead="Buy and sell shares of India's leading companies with lightning-fast order execution and a fully online experience."
      >
        <MpButton href="/register" size="lg">
          Start Trading Now
          <ArrowRight className="size-4" />
        </MpButton>
        <MpButton href="/register" variant="secondary" size="lg" className="border-mp-border text-mp-text">
          Open Demo Account
        </MpButton>
      </MpPageHero>

      {/* Stats strip */}
      <div className="border-b border-mp-border bg-mp-surface-2/60">
        <MpContainer>
          <dl className="grid grid-cols-2 divide-mp-border lg:grid-cols-4 lg:divide-x">
            {STATS.map((s, i) => (
              <div
                key={s.label}
                className={
                  "flex flex-col gap-1 px-2 py-7 text-center sm:py-9 " +
                  (i < 2 ? "border-b border-mp-border lg:border-b-0" : "")
                }
              >
                <dd className="mp-num text-2xl font-semibold text-mp-text sm:text-3xl">
                  {s.value}
                </dd>
                <dt className="text-xs font-medium uppercase tracking-wide text-mp-text-mut sm:text-[13px]">
                  {s.label}
                </dt>
              </div>
            ))}
          </dl>
        </MpContainer>
      </div>

      {/* Why equity */}
      <MpSection>
        <MpHeading
          eyebrow="Why equity"
          title="Why Trade Equity with SaudaSaacha?"
        />
        <MpProse className="mt-6">
          Trade equity delivery and intraday across NSE and BSE as a
          SEBI-registered broker. Open a Demat account with CDSL/NSDL and own
          shares of blue-chip companies like Reliance, TCS, HDFC Bank and
          Infosys. Enjoy T+1 settlement, advanced charts and real-time market
          depth — all from a single, fully online platform.
        </MpProse>
      </MpSection>

      {/* Top instruments */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading eyebrow="Instruments" title="Top Tradable Instruments" />
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
              {INSTRUMENTS.map((ins) => (
                <tr key={ins.symbol} className="border-b border-mp-border last:border-0">
                  <td className="mp-num px-5 py-4 font-semibold text-mp-text">{ins.symbol}</td>
                  <td className="px-5 py-4 text-mp-text-mut">{ins.exchange}</td>
                  <td className="mp-num px-5 py-4 text-mp-text-mut">{ins.lot}</td>
                  <td className="px-5 py-4 text-mp-text-mut">{ins.margin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </MpSection>

      {/* Why trade with us */}
      <MpSection>
        <MpHeading eyebrow="Why SaudaSaacha" title="Why Trade with SaudaSaacha" />
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <MpCard key={f.title} className="flex flex-col gap-4">
              <span className="grid size-11 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                <f.icon className="size-5" />
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
            Ready to Start Trading?
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            Open your Demat &amp; trading account today and invest across NSE,
            BSE &amp; MCX with SaudaSaacha.
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
