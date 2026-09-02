import type { Metadata } from "next";
import { ArrowRight, Check } from "lucide-react";
import {
  MpButton,
  MpContainer,
  MpHeading,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "Standard Account — Demat + Trading for Everyone | SaudaSaacha",
  description:
    "A complete Demat + trading account with access to Equity, Intraday, F&O and Commodities across NSE, BSE & MCX. Open your Standard Account in 5 minutes.",
};

const STATS = [
  { value: "5 min", label: "Account Opening" },
  { value: "All", label: "Segments" },
  { value: "7000+", label: "Stocks" },
  { value: "T+1", label: "Settlement" },
];

const FEATURES = [
  "Educational content & tutorials",
  "24x7 customer support",
  "Demat + trading account (CDSL/NSDL)",
  "Trade Equity, F&O, Commodities & IPO",
  "Transparent terms, no hidden conditions",
  "Add funds via UPI / Net Banking",
  "Real-time NSE, BSE & MCX data",
  "Mobile trading apps",
];

const COMPARE = {
  cols: ["Feature", "Standard", "Pro", "Paper"],
  rows: [
    ["Equity Delivery", "Included", "Included", "Virtual"],
    ["Intraday & F&O", "Included", "Included", "Virtual"],
    ["Commodities (MCX)", "Included", "Included", "Virtual"],
    ["Live option chain", "Yes", "Yes", "Yes"],
    ["Advanced charts", "Yes", "Yes", "Yes"],
    ["GTT & basket orders", "Yes", "Yes", "Yes"],
    ["API / algo access", "—", "Included", "—"],
    ["Margin", "SPAN + Exposure", "SPAN + Exposure", "SPAN + Exposure"],
    ["Support", "24x7", "Priority 24x7", "24x7"],
  ],
};

export default function StandardAccountPage() {
  return (
    <>
      <MpPageHero
        eyebrow="For Everyday Investors & Retail Traders"
        title="Standard Account"
        lead="Start your investing journey with SaudaSaacha. A complete Demat + trading account with access to Equity, Intraday, F&O and Commodities across NSE, BSE & MCX."
      >
        <MpButton href="/register" size="lg">
          Open Standard Account
          <ArrowRight className="size-4" />
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

      {/* Features */}
      <MpSection>
        <MpHeading eyebrow="What's included" title="Account Features" />
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <div key={f} className="flex items-start gap-3">
              <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                <Check className="size-3.5" />
              </span>
              <p className="text-sm leading-[1.6] text-mp-text">{f}</p>
            </div>
          ))}
        </div>
      </MpSection>

      {/* Compare */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading eyebrow="Compare" title="Compare Account Types" />
        <div className="mt-10 overflow-x-auto rounded-2xl border border-mp-border bg-mp-surface">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-mp-border text-xs uppercase tracking-wide text-mp-text-mut">
                {COMPARE.cols.map((c, i) => (
                  <th
                    key={c}
                    className={cnHead(i)}
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARE.rows.map((row) => (
                <tr key={row[0]} className="border-b border-mp-border last:border-0">
                  <td className="px-5 py-4 font-medium text-mp-text">{row[0]}</td>
                  <td className="px-5 py-4 font-medium text-mp-primary">{row[1]}</td>
                  <td className="px-5 py-4 text-mp-text-mut">{row[2]}</td>
                  <td className="px-5 py-4 text-mp-text-mut">{row[3]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Ready to Start Investing?
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            Open your Standard Account today and start trading across NSE, BSE &amp; MCX.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Open Standard Account
              <ArrowRight className="size-4" />
            </MpButton>
            <MpButton
              href="/register"
              variant="secondary"
              size="lg"
              className="w-full border-mp-border text-mp-text hover:border-mp-primary/60 sm:w-auto"
            >
              Try Paper Trading First
            </MpButton>
          </div>
        </MpContainer>
      </section>

      {/* Disclaimer */}
      <MpSection>
        <p className="mx-auto max-w-2xl text-center text-sm leading-[1.6] text-mp-text-mut">
          Investments in securities market are subject to market risks. Read all
          the related documents carefully before investing.
        </p>
      </MpSection>
    </>
  );
}

// Highlight the Standard column header (it's this page's account type).
function cnHead(i: number) {
  const base = "px-5 py-4 font-medium";
  return i === 1 ? `${base} text-mp-primary` : base;
}
