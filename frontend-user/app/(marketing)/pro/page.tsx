import type { Metadata } from "next";
import { ArrowRight, Check, Headset, LayoutDashboard, Zap } from "lucide-react";
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
  title: "Pro / Active Trader Account — Priority Support & API Access | SaudaSaacha",
  description:
    "An account built for high-volume F&O and intraday traders — priority support, advanced tools and API/algo access designed for serious traders.",
};

const STATS = [
  { label: "Support", value: "Priority" },
  { label: "Segments", value: "All" },
  { label: "API / Algo", value: "Yes" },
  { label: "Margin", value: "SPAN + Exp" },
];

const FEATURES = [
  "Priority 24x7 support",
  "Built for high-volume F&O & intraday traders",
  "Advanced charting & option-chain tools",
  "Dedicated relationship manager",
  "Faster order execution",
  "Premium market research",
  "Detailed F&O & margin analytics",
  "Exclusive market insights",
];

const HIGHLIGHTS = [
  {
    icon: Headset,
    title: "Dedicated Manager",
    body: "Get a personal relationship manager who understands your trading needs and provides tailored support.",
  },
  {
    icon: LayoutDashboard,
    title: "Advanced Tools",
    body: "Pro charting, option-chain and basket orders to manage your Nifty, Bank Nifty and stock F&O positions.",
  },
  {
    icon: Zap,
    title: "Faster Execution",
    body: "Quick, reliable order execution across Intraday, F&O and Commodity, built for high-volume traders.",
  },
];

export default function ProAccountPage() {
  return (
    <>
      <MpPageHero
        eyebrow="For Active & High-Volume Traders"
        title="Pro / Active Trader"
        lead="An account built for high-volume F&O and intraday traders — priority support, advanced tools and API/algo access designed for serious traders."
      >
        <MpButton href="/register" size="lg">
          Open Pro Account
          <ArrowRight className="size-4" />
        </MpButton>
      </MpPageHero>

      {/* Quick stats */}
      <MpSection>
        <MpStatGrid items={STATS} />
      </MpSection>

      {/* Premium features */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading align="center" eyebrow="Premium" title="Premium features" />
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

      {/* Highlights */}
      <MpSection>
        <MpHeading
          align="center"
          eyebrow="Why Pro"
          title="Built for serious traders"
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {HIGHLIGHTS.map((h) => (
            <MpCard key={h.title} className="flex flex-col gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                <h.icon className="size-6" />
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {h.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{h.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Elevate your trading
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            Trade smarter. Open a Pro / Active Trader account and get advanced
            tools with priority support.
          </p>
          <div className="mt-9 flex justify-center">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Open Pro Account
              <ArrowRight className="size-4" />
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
