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
  title: "IB Management — Introducing Broker Program | SaudaSaacha",
  description:
    "Refer traders to SaudaSaacha and earn recurring commission. A real-time dashboard, multi-tier tracking, and on-time monthly payouts in ₹.",
};

const FEATURES = [
  {
    title: "Real-time dashboard",
    body: "Track sign-ups, active traders, and commission earned as it happens — no waiting for end-of-month reports.",
  },
  {
    title: "Multi-tier tracking",
    body: "Build a sub-IB network and earn across tiers. Every referral is attributed cleanly and transparently.",
  },
  {
    title: "On-time monthly payouts",
    body: "Commissions are paid every month to your bank or UPI, once you cross the minimum threshold. No clawbacks on legitimate referrals.",
  },
  {
    title: "Marketing support",
    body: "Banners, honest talking points, and a dedicated manager once you reach volume. We help you grow.",
  },
];

const WHO = [
  "Trading educators and course creators",
  "Signal and community owners",
  "Finance creators on YouTube, Telegram & X",
  "Active traders and investors wanting a second income",
];

export default function IbManagementPage() {
  return (
    <>
      <MpPageHero
        eyebrow="IB Management"
        title="Refer traders. Earn recurring commission."
        lead="The SaudaSaacha Introducing Broker program pays you for every trader you bring on — with a real-time dashboard, multi-tier tracking, and on-time monthly payouts in ₹."
      >
        <MpButton href="/register" size="lg">
          Become an IB
          <ArrowRight className="size-4" />
        </MpButton>
        <MpButton href="/contact" variant="secondary" size="lg" className="border-mp-border text-mp-text">
          Talk to us
        </MpButton>
      </MpPageHero>

      <MpSection>
        <MpHeading eyebrow="What you get" title="Built for partners who scale" />
        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <MpCard key={f.title} className="flex flex-col gap-3">
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {f.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{f.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      <MpSection className="bg-mp-surface-2/60">
        <MpHeading eyebrow="Who it's for" title="Who partners with us" />
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {WHO.map((w) => (
            <div key={w} className="flex items-start gap-3">
              <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-mp-primary/10 text-mp-primary">
                <Check className="size-3.5" />
              </span>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{w}</p>
            </div>
          ))}
        </div>
        <div className="mt-10">
          <MpButton href="/register">
            Become an IB
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>
    </>
  );
}
