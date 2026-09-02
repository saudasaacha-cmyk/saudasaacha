import { BackgroundGradientAnimation } from "@/components/ui/background-gradient-animation";
import HeroHeadline from "./HeroHeadline";

export default function OptibizHero() {
  return (
    <section
      id="home"
      className="relative overflow-hidden text-white min-h-screen flex items-center"
      style={{ background: 'linear-gradient(160deg, #0d0d0d 0%, #1a1a1a 55%, #C4161C 100%)' }}
    >
      {/* Animated gradient background — themed navy + gold */}
      <BackgroundGradientAnimation
        interactive={false}
        containerClassName="absolute inset-0 h-full w-full"
        gradientBackgroundStart="rgb(15, 34, 56)"
        gradientBackgroundEnd="rgb(17, 39, 68)"
        firstColor="rgb(31, 70, 119)"
        secondColor="150, 124, 64"
        thirdColor="47, 89, 144"
        fourthColor="47, 89, 144"
        fifthColor="38, 78, 126"
        pointerColor="150, 124, 64"
        size="85%"
        blendingValue="soft-light"
      />

      {/* Subtle grid texture over the gradient */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.06]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.6) 1px, transparent 1px)',
          backgroundSize: '54px 54px',
        }}
      />

      {/* ── Hero content (centered) ─────────────────────────────── */}
      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 py-24 flex flex-col items-center text-center">

        <div className="mb-8">
          <HeroHeadline />
        </div>

        <p className="text-base md:text-lg text-slate-300 leading-relaxed max-w-2xl mb-10">
          Trade equities, F&amp;O, commodities, forex, US stocks and crypto — all from one
          fast, transparent, zero-hassle platform built for serious Indian traders.
        </p>

        {/* Active traders badge */}
        <div className="inline-flex items-center gap-2.5 bg-[#E6B839] text-[#C4161C] rounded-full px-5 py-2.5 shadow-lg">
          <span className="text-xl font-bold font-manrope leading-none">150K+</span>
          <span className="text-sm font-semibold">Active Traders</span>
        </div>
      </div>
    </section>
  );
}
