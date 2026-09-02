import type { Metadata } from "next";
import { ArrowRight, Coins, Flame, PieChart } from "lucide-react";
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
  title: "Trade Commodities on MCX — Gold, Silver & Crude Oil | SaudaSaacha",
  description:
    "Diversify with Gold, Silver, Crude Oil and more on the Multi Commodity Exchange of India. Transparent SPAN + Exposure margins and extended evening sessions.",
};

const STATS = [
  { label: "Exchange", value: "MCX" },
  { label: "Commodities", value: "15+" },
  { label: "Margin", value: "SPAN + Exposure" },
  { label: "Market Hours", value: "9 AM – 11:30 PM" },
];

const INSTRUMENTS: [string, string, string, string][] = [
  ["GOLD", "MCX", "100 grams", "SPAN + Exposure"],
  ["SILVER", "MCX", "30 kg", "SPAN + Exposure"],
  ["CRUDEOIL", "MCX", "100 barrels", "SPAN + Exposure"],
  ["NATURALGAS", "MCX", "1250 mmBtu", "SPAN + Exposure"],
  ["COPPER", "MCX", "2500 kg", "SPAN + Exposure"],
  ["GOLDM (Gold Mini)", "MCX", "10 grams", "SPAN + Exposure"],
];

const FEATURES = [
  {
    icon: Coins,
    title: "Trade Precious Metals",
    body: "Access MCX Gold, Silver and their mini contracts with transparent SPAN + Exposure margins.",
  },
  {
    icon: Flame,
    title: "Energy Markets",
    body: "Trade Crude Oil and Natural Gas futures on MCX with real-time pricing through extended evening sessions.",
  },
  {
    icon: PieChart,
    title: "Portfolio Diversification",
    body: "Hedge against equity volatility and inflation by adding MCX commodities to your investment portfolio.",
  },
];

export default function CommoditiesPage() {
  return (
    <>
      <MpPageHero
        eyebrow="MCX"
        title="Trade Commodities on MCX"
        lead="Diversify your portfolio with Gold, Silver, Crude Oil and more on the Multi Commodity Exchange of India."
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

      {/* Why trade commodities */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading eyebrow="Overview" title="Why trade commodities?" />
        <MpProse className="mt-6">
          Commodities offer excellent diversification and act as a hedge against
          inflation. Trade precious metals like Gold and Silver, and energy
          contracts like Crude Oil and Natural Gas on the MCX (Multi Commodity
          Exchange) as a SEBI-registered broker. Enjoy transparent SPAN +
          Exposure margins and access to Indian commodity futures from 9 AM to
          11:30 PM.
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
          Lot sizes and contract specifications are set by the exchange and
          revised periodically. Check the latest details before you trade.
        </p>
      </MpSection>

      {/* Why trade with us */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading
          align="center"
          eyebrow="Why SaudaSaacha"
          title="Why trade commodities with us"
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
