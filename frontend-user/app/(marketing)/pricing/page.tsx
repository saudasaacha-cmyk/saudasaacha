import type { Metadata } from "next";
import { ArrowRight, Check } from "lucide-react";
import {
  MpButton,
  MpCard,
  MpHeading,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "Pricing — Transparent Brokerage on NSE, BSE & MCX | SaudaSaacha",
  description:
    "Simple, transparent brokerage. Free equity delivery, flat per-order intraday & F&O charges, and zero fees on direct mutual funds and IPOs.",
};

const BROKERAGE: [string, string][] = [
  ["Equity Delivery", "₹0 — free"],
  ["Equity Intraday", "₹20 or 0.03% per order (whichever is lower)"],
  ["Equity Futures", "₹20 or 0.03% per order (whichever is lower)"],
  ["Equity Options", "₹20 flat per order"],
  ["Commodity (MCX)", "₹20 or 0.03% per order (whichever is lower)"],
  ["Currency F&O", "₹20 or 0.03% per order (whichever is lower)"],
  ["Direct Mutual Funds", "₹0 — free"],
  ["IPO Application (UPI)", "₹0 — free"],
];

const ACCOUNT = [
  { title: "Account Opening", value: "₹0", note: "Open a Demat & trading account online, free." },
  { title: "Maintenance (AMC)", value: "Low yearly", note: "A small annual demat maintenance charge applies." },
  { title: "Funding", value: "₹0 fees", note: "Add funds via UPI or Net Banking with no deposit fees." },
];

const INCLUDED = [
  "Equity, F&O, Commodities, IPO & Mutual Funds in one account",
  "Web terminal, mobile app and desktop platform",
  "Live NSE & BSE option chain and advanced charts",
  "GTT, basket orders and price alerts",
  "100+ technical indicators",
  "Support in English and Hindi during IST hours",
];

export default function PricingPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Pricing"
        title="Simple, transparent brokerage."
        lead="Free equity delivery, flat per-order charges on intraday and F&O, and zero fees on direct mutual funds and IPOs. No hidden conditions."
      >
        <MpButton href="/register" size="lg">
          Open Account
          <ArrowRight className="size-4" />
        </MpButton>
      </MpPageHero>

      {/* Brokerage table */}
      <MpSection>
        <MpHeading align="center" eyebrow="Brokerage" title="Brokerage by segment" />
        <div className="mx-auto mt-10 max-w-3xl overflow-x-auto rounded-2xl border border-mp-border bg-mp-surface">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead>
              <tr className="border-b border-mp-border text-xs uppercase tracking-wide text-mp-text-mut">
                <th className="px-5 py-4 font-medium">Segment</th>
                <th className="px-5 py-4 font-medium">Brokerage</th>
              </tr>
            </thead>
            <tbody>
              {BROKERAGE.map((row) => (
                <tr key={row[0]} className="border-b border-mp-border last:border-0">
                  <td className="px-5 py-4 font-semibold text-mp-text">{row[0]}</td>
                  <td className="mp-num px-5 py-4 text-mp-text-mut">{row[1]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mx-auto mt-4 max-w-3xl text-xs text-mp-text-mut">
          Indicative pricing. Statutory charges — STT, exchange transaction
          charges, GST, SEBI turnover fees and stamp duty — apply as per
          prevailing regulations and are shown clearly before you place an order.
        </p>
      </MpSection>

      {/* Account charges */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading align="center" eyebrow="Account" title="Account & funding charges" />
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {ACCOUNT.map((a) => (
            <MpCard key={a.title} className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-mp-text-mut">
                {a.title}
              </span>
              <span className="font-display text-3xl font-bold text-mp-primary">
                {a.value}
              </span>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{a.note}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* What's included */}
      <MpSection>
        <MpHeading align="center" eyebrow="Included" title="What every account includes" />
        <div className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-2">
          {INCLUDED.map((item) => (
            <div key={item} className="flex items-start gap-3">
              <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                <Check className="size-3.5" />
              </span>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{item}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 flex justify-center">
          <MpButton href="/register" size="lg">
            Open Account
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>
    </>
  );
}
