import type { Metadata } from "next";
import {
  ArrowRight,
  BarChart3,
  BellRing,
  Check,
  Globe,
  MousePointerClick,
} from "lucide-react";
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
  title: "SaudaSaacha Web Terminal — Trade NSE, BSE & MCX in Your Browser",
  description:
    "No download required. Launch the SaudaSaacha Web Terminal from any browser and trade Indian markets in seconds — advanced charts, live option chain and all order types.",
};

const FEATURES = [
  {
    icon: Globe,
    title: "Browser-Based Trading",
    body: "No downloads required. Trade NSE, BSE & MCX from any device with a web browser.",
  },
  {
    icon: BarChart3,
    title: "Advanced Charts & Option Chain",
    body: "Pro-grade charting with 100+ indicators, drawing tools, and a live NSE/BSE option chain.",
  },
  {
    icon: MousePointerClick,
    title: "One-Click Execution",
    body: "Place equity, intraday, F&O and commodity orders instantly with lightning-fast execution.",
  },
  {
    icon: BellRing,
    title: "GTT & Price Alerts",
    body: "Set Good-Till-Triggered (GTT) orders and price alerts on Nifty 50, Bank Nifty & your stocks.",
  },
];

const CHECKLIST = [
  "Advanced charts with 100+ indicators",
  "Live NSE & BSE option chain",
  "GTT & basket orders",
  "Holdings, positions & margin tracker",
  "SPAN + Exposure margin calculator",
  "Intraday, delivery, F&O & commodity order types",
  "Custom watchlists for stocks & indices",
  "Order & trade history with analytics",
  "Instant UPI funding",
  "Secure SSL encryption",
];

export default function WebTerminalPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Web Platform"
        title="SaudaSaacha Web Terminal — trade NSE, BSE & MCX instantly, anywhere"
        lead="No download required. Launch the SaudaSaacha Web Terminal from any browser and start trading Indian markets in seconds."
      >
        <MpButton href="/register" size="lg">
          Launch Web Terminal
          <ArrowRight className="size-4" />
        </MpButton>
        <MpButton href="/register" variant="secondary" size="lg" className="border-mp-border text-mp-text">
          Open Demat Account
        </MpButton>
      </MpPageHero>

      {/* Feature grid */}
      <MpSection>
        <MpHeading
          align="center"
          eyebrow="Features"
          title="Everything you need to trade Indian markets"
        />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <MpCard key={f.title} className="flex flex-col gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                <f.icon className="size-6" />
              </span>
              <h3 className="font-display text-base font-semibold text-mp-text">
                {f.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{f.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* Professional trading, simplified */}
      <MpSection className="bg-mp-surface-2/60">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div>
            <MpHeading
              eyebrow="The terminal"
              title="Professional trading, simplified"
            />
            <MpProse className="mt-6">
              The SaudaSaacha Web Terminal combines powerful tools with an
              intuitive interface. Whether you&apos;re a first-time investor or an
              active F&O trader, you&apos;ll find everything you need to invest in
              equity, derivatives and commodities.
            </MpProse>
            <ul className="mt-8 grid gap-3 sm:grid-cols-2">
              {CHECKLIST.map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm text-mp-text">
                  <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                    <Check className="size-3" />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Stylised terminal mock */}
          <div className="rounded-2xl border border-mp-border bg-mp-surface p-4 shadow-sm">
            <div className="flex items-center gap-2 border-b border-mp-border pb-3">
              <span className="size-3 rounded-full bg-loss/70" />
              <span className="size-3 rounded-full bg-mp-gold/70" />
              <span className="size-3 rounded-full bg-mp-primary/70" />
              <span className="ml-3 text-xs font-medium text-mp-text-mut">
                SaudaSaacha Web Terminal
              </span>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-3">
              <div className="col-span-2 flex h-40 items-end gap-2 rounded-xl bg-mp-surface-2/70 p-4">
                {[40, 64, 52, 78, 60, 88, 72, 96].map((h, i) => (
                  <span
                    key={i}
                    className="flex-1 rounded-t bg-gradient-to-t from-mp-primary to-mp-primary-2"
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
              <div className="flex flex-col gap-2 rounded-xl bg-mp-surface-2/70 p-3">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-mp-text-mut">
                  Option chain
                </span>
                {[0, 1, 2, 3, 4].map((r) => (
                  <div key={r} className="flex items-center justify-between gap-2">
                    <span className="h-2 w-8 rounded-full bg-mp-primary/30" />
                    <span className="h-2 w-6 rounded-full bg-mp-text-mut/25" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </MpSection>

      {/* Access anywhere */}
      <MpSection>
        <div className="flex flex-col items-start justify-between gap-6 rounded-2xl border border-mp-border bg-mp-surface p-8 sm:flex-row sm:items-center sm:p-10">
          <div className="max-w-2xl">
            <h2 className="font-display text-2xl font-bold text-mp-text sm:text-3xl">
              Access anywhere
            </h2>
            <p className="mt-3 text-base leading-[1.6] text-mp-text-mut">
              Trade from your desktop, laptop, tablet, or smartphone — or switch
              to the SaudaSaacha Mobile App (iOS &amp; Android). Your Demat
              account syncs seamlessly across all devices.
            </p>
          </div>
          <MpButton href="/register" className="shrink-0">
            Launch Web Terminal
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Start trading in seconds
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            No downloads, no installations. Just open your browser and trade NSE,
            BSE &amp; MCX with pro-grade tools.
          </p>
          <div className="mt-9 flex justify-center">
            <MpButton href="/register" size="lg" className="w-full sm:w-auto">
              Open Demat Account
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
