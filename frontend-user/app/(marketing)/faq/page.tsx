import type { Metadata } from "next";
import { ArrowRight, Plus } from "lucide-react";
import { MpButton, MpPageHero, MpSection } from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "FAQs | SaudaSaacha — Trading & Investing on NSE, BSE & MCX",
  description:
    "Answers about SaudaSaacha: opening a Demat account, what you can trade, fund and securities safety, platforms, IPOs, mutual funds and charges.",
};

const GROUPS: { heading: string; items: { q: string; a: string }[] }[] = [
  {
    heading: "Account",
    items: [
      {
        q: "How do I open a Demat & trading account?",
        a: "Complete a 100% online e-KYC with your PAN and Aadhaar. Most accounts are ready to trade within minutes — no paperwork or branch visit needed.",
      },
      {
        q: "Is account opening free?",
        a: "Yes, opening a Demat & trading account is free. A small annual demat maintenance charge applies — see the Pricing page for details.",
      },
      {
        q: "Are my securities and funds safe?",
        a: "Your securities are held in your own demat account with the depository (CDSL/NSDL), and your funds move only through regulated banking channels.",
      },
    ],
  },
  {
    heading: "Trading",
    items: [
      {
        q: "What can I trade on SaudaSaacha?",
        a: "Equity Delivery and Intraday, Futures & Options, Commodities on MCX, IPOs and Mutual Funds — all from a single account.",
      },
      {
        q: "What are the market hours?",
        a: "Equity and F&O trade 9:15 AM to 3:30 PM IST on market days. MCX commodities trade until 11:30 PM IST. No weekends or exchange holidays.",
      },
      {
        q: "Can I apply for IPOs and invest in mutual funds?",
        a: "Yes. Apply to mainboard and SME IPOs via UPI, and invest in direct mutual funds — all from the same platform.",
      },
      {
        q: "Do you offer API / algo trading?",
        a: "Yes. API and algo access is available on Pro and HNI/Algo accounts so you can build and deploy your own strategies.",
      },
    ],
  },
  {
    heading: "Platforms",
    items: [
      {
        q: "Which platforms can I trade on?",
        a: "A browser-based web terminal, iOS and Android apps, and a pro-grade desktop platform. Your account works seamlessly across all of them.",
      },
      {
        q: "Can I practise before trading real money?",
        a: "Yes. Use Paper / Virtual Trading to practise on live NSE, BSE & MCX prices with virtual funds — no KYC and no real money required.",
      },
    ],
  },
  {
    heading: "Pricing & payments",
    items: [
      {
        q: "How much is the brokerage?",
        a: "Equity delivery is free. Intraday and F&O are charged at a low flat per-order rate, and direct mutual funds and IPO applications are free. See the Pricing page.",
      },
      {
        q: "How do I add funds?",
        a: "Add money instantly via UPI, Net Banking or NEFT/RTGS/IMPS. There are no deposit fees from our side.",
      },
      {
        q: "Are there hidden charges?",
        a: "No. Statutory charges (STT, exchange, GST, SEBI and stamp duty) are shown clearly before you place any order, so there are no surprises.",
      },
    ],
  },
];

export default function FaqPage() {
  return (
    <>
      <MpPageHero
        eyebrow="FAQs"
        title="Frequently asked questions."
        lead="Everything you need to know about trading and investing with SaudaSaacha. Can't find what you're looking for? Contact our team."
      >
        <MpButton href="/contact" size="lg">
          Contact our team
          <ArrowRight className="size-4" />
        </MpButton>
      </MpPageHero>

      {GROUPS.map((group, gi) => (
        <MpSection key={group.heading} className={gi % 2 === 1 ? "bg-mp-surface-2/60" : ""}>
          <h2 className="font-display text-2xl font-bold text-mp-text">
            {group.heading}
          </h2>
          <div className="mt-6 flex flex-col gap-3">
            {group.items.map((item) => (
              <details
                key={item.q}
                className="group rounded-2xl border border-mp-border bg-mp-surface p-5 [&_summary::-webkit-details-marker]:hidden"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                  <span className="font-display text-base font-semibold text-mp-text">
                    {item.q}
                  </span>
                  <Plus className="size-5 shrink-0 text-mp-primary transition-transform duration-200 group-open:rotate-45" />
                </summary>
                <p className="mt-3 text-sm leading-[1.65] text-mp-text-mut">
                  {item.a}
                </p>
              </details>
            ))}
          </div>
        </MpSection>
      ))}

      <MpSection>
        <div className="flex flex-col items-start gap-4 rounded-2xl border border-mp-border bg-mp-surface p-8 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-base text-mp-text">
            Can&apos;t find what you&apos;re looking for?
          </p>
          <MpButton href="/contact" variant="secondary">
            Contact our team
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>
    </>
  );
}
