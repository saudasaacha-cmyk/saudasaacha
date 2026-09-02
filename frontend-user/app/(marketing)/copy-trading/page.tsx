import type { Metadata } from "next";
import {
  ArrowRight,
  BadgePercent,
  Check,
  Headset,
  LayoutDashboard,
  Megaphone,
  Network,
  Trophy,
} from "lucide-react";
import {
  MpButton,
  MpCard,
  MpContainer,
  MpHeading,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Partner & Sub-Broker Program — Earn Recurring Brokerage | SaudaSaacha",
  description:
    "Become an Authorised Person, sub-broker or referral partner with SaudaSaacha and earn a recurring share of brokerage by onboarding new clients.",
};

const BENEFITS = [
  {
    icon: BadgePercent,
    title: "Competitive Revenue Share",
    body: "Earn an attractive share of the brokerage your clients generate with our tiered revenue-share structure. The more clients you onboard, the higher your tier.",
  },
  {
    icon: Network,
    title: "Multi-Level Sub-Brokers",
    body: "Earn from sub-brokers under your network. Build a team of Authorised Persons and generate recurring income across multiple levels.",
  },
  {
    icon: LayoutDashboard,
    title: "Real-Time Dashboard",
    body: "Track referrals, brokerage earned, client activity, and payouts in real time through your dedicated partner portal.",
  },
  {
    icon: Megaphone,
    title: "Marketing Materials",
    body: "Access banners, landing pages, tracking links, and promotional content to grow your client base.",
  },
  {
    icon: Trophy,
    title: "Performance Bonuses",
    body: "Unlock bonus tiers based on monthly brokerage volume. Top-performing partners receive additional rewards and incentives.",
  },
  {
    icon: Headset,
    title: "Dedicated Partner Manager",
    body: "Get a personal relationship manager to help you onboard clients, resolve issues, and scale your sub-broking business.",
  },
];

const TIERS = [
  {
    name: "Referral",
    sub: "Entry partner tier",
    share: "Standard share",
    note: "Of client brokerage",
    featured: false,
  },
  {
    name: "Authorised Person",
    sub: "Growing client base",
    share: "Higher share",
    note: "Of client brokerage",
    featured: true,
  },
  {
    name: "Master Sub-Broker",
    sub: "Established network",
    share: "Top share",
    note: "Of client brokerage",
    featured: false,
  },
];

const STEPS = [
  { n: "01", title: "Apply", body: "Fill out the partner application form with your details." },
  { n: "02", title: "Get Approved", body: "Our team reviews and onboards you as an Authorised Person." },
  { n: "03", title: "Share Your Link", body: "Use your unique referral link to onboard clients." },
  { n: "04", title: "Earn Brokerage Share", body: "Get paid for the brokerage your referred clients generate." },
];

const PORTAL_FEATURES = [
  "Real-time brokerage-share tracking",
  "Client activity monitoring",
  "Sub-broker management tools",
  "Automated payout system",
  "Custom referral links",
  "Detailed reporting & analytics",
  "Marketing resource library",
  "Priority support channel",
];

export default function CopyTradingPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Partner Program"
        title="Partner & Sub-Broker Program"
        lead="Become an Authorised Person (AP), sub-broker, or referral partner with SaudaSaacha and earn a recurring share of brokerage by onboarding new clients. Build your broking business with our support."
      >
        <MpButton href="/contact" size="lg">
          Become a Partner
          <ArrowRight className="size-4" />
        </MpButton>
        <MpButton href="#why" variant="secondary" size="lg" className="border-mp-border text-mp-text">
          Learn More
        </MpButton>
      </MpPageHero>

      {/* Why partner */}
      <MpSection id="why">
        <MpHeading
          align="center"
          eyebrow="Why Partner With Us"
          title="Build a successful broking business"
          lead="Everything you need to build a successful Authorised Person & sub-broker business."
        />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {BENEFITS.map((b) => (
            <MpCard key={b.title} className="flex flex-col gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                <b.icon className="size-6" />
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {b.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{b.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* Revenue-share tiers */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading align="center" eyebrow="Tiers" title="Revenue-share tiers" />
        <div className="mt-12 grid items-stretch gap-5 lg:grid-cols-3">
          {TIERS.map((t) => (
            <MpCard
              key={t.name}
              className={cn(
                "flex flex-col gap-2",
                t.featured && "ring-1 ring-mp-primary/40",
              )}
            >
              {t.featured ? (
                <span className="w-fit rounded-full bg-mp-primary/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-mp-primary">
                  Most popular
                </span>
              ) : null}
              <h3 className="font-display text-xl font-bold text-mp-text">
                {t.name}
              </h3>
              <p className="text-sm text-mp-text-mut">{t.sub}</p>
              <div className="mt-4 border-t border-mp-border pt-4">
                <div className="font-display text-2xl font-bold text-mp-primary">
                  {t.share}
                </div>
                <div className="mt-1 text-xs text-mp-text-mut">{t.note}</div>
              </div>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* How to get started */}
      <MpSection>
        <MpHeading align="center" eyebrow="Get Started" title="How to get started" />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <MpCard key={s.n} className="flex flex-col gap-4">
              <span className="mp-num font-display text-3xl font-bold text-mp-primary/70">
                {s.n}
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {s.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{s.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* Portal features */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading align="center" eyebrow="Portal" title="Partner portal features" />
        <div className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-2">
          {PORTAL_FEATURES.map((f) => (
            <div key={f} className="flex items-center gap-3">
              <span className="grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                <Check className="size-3.5" />
              </span>
              <span className="text-sm text-mp-text">{f}</span>
            </div>
          ))}
        </div>
      </MpSection>

      {/* CTA band */}
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-texture absolute inset-0 opacity-50" aria-hidden />
        <MpContainer className="relative py-20 text-center sm:py-24">
          <h2 className="mx-auto max-w-3xl font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
            Unlimited earning potential
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-[1.6] text-mp-text-mut">
            No caps on your revenue share. The more clients you onboard, the more
            you earn — every month, for life.
          </p>
          <div className="mt-9 flex justify-center">
            <MpButton href="/contact" size="lg" className="w-full sm:w-auto">
              Apply Now
              <ArrowRight className="size-4" />
            </MpButton>
          </div>
        </MpContainer>
      </section>
    </>
  );
}
