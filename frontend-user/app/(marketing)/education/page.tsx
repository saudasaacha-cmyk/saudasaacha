import type { Metadata } from "next";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Clock,
  GraduationCap,
  Landmark,
  Layers,
  PlayCircle,
  Smartphone,
  Target,
  Trophy,
} from "lucide-react";
import {
  MpButton,
  MpCard,
  MpHeading,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";

export const metadata: Metadata = {
  title: "Trading Tutorials — Learn to Trade NSE, BSE & MCX | SaudaSaacha",
  description:
    "Learn to trade the Indian markets at your own pace with comprehensive video courses and tutorials — from stock-market basics to F&O and intraday strategies.",
};

const COURSES = [
  {
    icon: BookOpen,
    level: "Beginner",
    title: "Stock Market Basics for Beginners",
    body: "Learn how the Indian stock market works — NSE, BSE, Demat accounts, SEBI, and placing your first Delivery and Intraday trades.",
    duration: "2 hours",
    lessons: "12 lessons",
  },
  {
    icon: BarChart3,
    level: "Intermediate",
    title: "Technical Analysis & Charting",
    body: "Master candlestick patterns, chart indicators, and technical analysis used to trade Nifty 50, Bank Nifty and individual stocks.",
    duration: "4 hours",
    lessons: "20 lessons",
  },
  {
    icon: Layers,
    level: "Intermediate",
    title: "Futures & Options Mastery",
    body: "Understand F&O — option chain, expiry, premiums, SPAN + Exposure margin and proven strategies on index and stock derivatives.",
    duration: "3 hours",
    lessons: "15 lessons",
  },
  {
    icon: Target,
    level: "Advanced",
    title: "Intraday Trading Strategies",
    body: "Learn momentum, breakout and scalping strategies for Intraday trading on NSE & BSE, with strict risk management.",
    duration: "5 hours",
    lessons: "25 lessons",
  },
  {
    icon: Landmark,
    level: "Beginner",
    title: "IPO & Long-Term Investing",
    body: "Apply for IPOs, analyse companies with fundamental analysis, and build a long-term portfolio of stocks and mutual funds.",
    duration: "3 hours",
    lessons: "14 lessons",
  },
];

const WHY = [
  {
    icon: GraduationCap,
    title: "Expert Instructors",
    body: "Learn from professional traders with years of experience.",
  },
  {
    icon: Smartphone,
    title: "Learn Anywhere",
    body: "Access courses on any device, anytime, anywhere.",
  },
  {
    icon: Trophy,
    title: "Practical Skills",
    body: "Apply what you learn immediately in your trading.",
  },
];

export default function EducationPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Trading Tutorials"
        title="Learn to trade the Indian markets"
        lead="Learn to trade the Indian markets — NSE, BSE & MCX — at your own pace with our comprehensive video courses and tutorials."
      >
        <MpButton href="/register" size="lg">
          Browse All Courses
          <ArrowRight className="size-4" />
        </MpButton>
      </MpPageHero>

      {/* Featured courses */}
      <MpSection>
        <MpHeading eyebrow="Courses" title="Featured Courses" />
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {COURSES.map((c) => (
            <MpCard key={c.title} className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="grid size-11 place-items-center rounded-xl bg-mp-primary/10 text-mp-primary">
                  <c.icon className="size-5" />
                </span>
                <span className="rounded-full bg-mp-surface-2 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-mp-text-mut">
                  {c.level}
                </span>
              </div>
              <h3 className="font-display text-lg font-semibold leading-snug text-mp-text">
                {c.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{c.body}</p>
              <div className="mt-1 flex items-center gap-4 text-xs font-medium text-mp-text-mut">
                <span className="flex items-center gap-1.5">
                  <Clock className="size-3.5" />
                  {c.duration}
                </span>
                <span className="flex items-center gap-1.5">
                  <PlayCircle className="size-3.5" />
                  {c.lessons}
                </span>
              </div>
              <MpButton href="/register" variant="secondary" className="mt-auto w-full">
                Start Learning
                <ArrowRight className="size-4" />
              </MpButton>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* Why learn */}
      <MpSection className="bg-mp-surface-2/60">
        <MpHeading
          align="center"
          eyebrow="Why SaudaSaacha"
          title="Why Learn with SaudaSaacha?"
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {WHY.map((w) => (
            <MpCard key={w.title} className="flex flex-col items-center gap-4 text-center">
              <span className="grid size-12 place-items-center rounded-2xl bg-mp-primary/10 text-mp-primary">
                <w.icon className="size-6" />
              </span>
              <h3 className="font-display text-lg font-semibold text-mp-text">
                {w.title}
              </h3>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{w.body}</p>
            </MpCard>
          ))}
        </div>
      </MpSection>

      {/* CTA + disclaimer */}
      <MpSection>
        <div className="flex flex-col items-center gap-6 text-center">
          <MpButton href="/register" size="lg">
            Browse All Courses
            <ArrowRight className="size-4" />
          </MpButton>
          <p className="max-w-2xl text-sm leading-[1.6] text-mp-text-mut">
            Investments in securities market are subject to market risks. Read
            all the related documents carefully before investing.
          </p>
        </div>
      </MpSection>
    </>
  );
}
