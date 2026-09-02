import type { Metadata } from "next";
import { ArrowRight, CalendarClock, Globe2, ShieldCheck } from "lucide-react";
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
  title: "Indices — Trade Nifty 50, Bank Nifty & Sensex | SaudaSaacha",
  description:
    "Get exposure to Nifty 50, Bank Nifty and Sensex through index futures & options on NSE and BSE. Weekly & monthly expiries, transparent SPAN + Exposure margins.",
};

const STATS = [
  { value: "NSE / BSE", label: "Exchanges" },
  { value: "10+", label: "Indices" },
  { value: "SPAN + Exposure", label: "Margin" },
  { value: "Weekly & Monthly", label: "Expiries" },
];

const INSTRUMENTS = [
  { symbol: "NIFTY 50", exchange: "NFO", lot: "75", margin: "SPAN + Exposure" },
  { symbol: "BANK NIFTY", exchange: "NFO", lot: "30", margin: "SPAN + Exposure" },
  { symbol: "FIN NIFTY", exchange: "NFO", lot: "65", margin: "SPAN + Exposure" },
  { symbol: "SENSEX", exchange: "BFO (BSE)", lot: "20", margin: "SPAN + Exposure" },
  { symbol: "NIFTY MIDCAP", exchange: "NFO", lot: "120", margin: "SPAN + Exposure" },
  { symbol: "BANKEX", exchange: "BFO (BSE)", lot: "30", margin: "SPAN + Exposure" },
];

const FEATURES = [
  {
    icon: Globe2,
    title: "Broad Market Exposure",
    body: "Trade Nifty 50, Bank Nifty, Fin Nifty and Sensex to take a position on entire sectors and the Indian market.",
  },
  {
    icon: ShieldCheck,
    title: "Transparent Margins",
    body: "Carry index positions with SEBI's SPAN + Exposure margins — transparent, exchange-mandated and predictable.",
  },
  {
    icon: CalendarClock,
    title: "Weekly & Monthly Expiries",
    body: "Choose from weekly and monthly contracts to build short-term strategies or longer-term index views.",
  },
];

export default function IndicesPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Indices"
        title="Trade India's Top Indices"
        lead="Get exposure to Nifty 50, Bank Nifty and Sensex through index futures & options on NSE and BSE."
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

      {/* What is index trading */}
      <MpSection>
        <MpHeading eyebrow="Overview" title="What is Index Trading?" />
        <MpProse className="mt-6">
          Index trading lets you take a view on the broader Indian market or a
          sector without buying individual stocks. Trade index futures and
          options on Nifty 50, Bank Nifty, Fin Nifty and the Sensex through the
          NSE and BSE derivatives segments. Go long or short, choose weekly or
          monthly expiries, and carry positions with transparent SPAN + Exposure
          margins.
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
