"use client";

import { Star, Quote } from 'lucide-react';
import { useScrollAnimation, useStaggerAnimation } from './hooks/useScrollAnimation';

const testimonials = [
  {
    name: 'Vikram Nair',
    role: 'Full-time Trader, Mumbai',
    avatar: 'VN',
    rating: 5,
    review:
      'SachchaSauda has completely transformed how I trade. The flat ₹20 brokerage alone saves me thousands every month. The execution speed is unmatched — orders fill in milliseconds.',
    color: 'bg-brand-600',
    market: 'NSE & Derivatives',
  },
  {
    name: 'Emily Johnson',
    role: 'Forex Trader, New York',
    avatar: 'EJ',
    rating: 5,
    review:
      'I have tried many platforms but SachchaSauda stands out for its clean interface and tight spreads on forex pairs. The mobile app is incredibly smooth and reliable.',
    color: 'bg-violet-600',
    market: 'Forex & Crypto',
  },
  {
    name: 'Lucas Müller',
    role: 'Retail Investor, Frankfurt',
    avatar: 'LM',
    rating: 5,
    review:
      'As a beginner, I was worried about complexity. SachchaSauda made it so easy to start. The educational resources and daily market insights helped me grow my portfolio by 28% in 6 months.',
    color: 'bg-emerald-600',
    market: 'Stocks & ETFs',
  },
  {
    name: 'Yuki Tanaka',
    role: 'Portfolio Manager, Tokyo',
    avatar: 'YT',
    rating: 5,
    review:
      'The advanced charting tools and technical indicators are on par with professional-grade software. Managing multiple client accounts is seamless with the multi-account feature.',
    color: 'bg-amber-600',
    market: 'Multi-Asset',
  },
];

export default function Testimonials() {
  const { ref: bannerRef } = useScrollAnimation(0.1);
  const { ref: headerRef } = useScrollAnimation(0.1);
  const { ref: ratingRef } = useScrollAnimation(0.1);
  const cardsRef = useStaggerAnimation(0.08, 100);

  return (
    <section className="py-0">

      {/* ── Blue Banner Quote ── */}
      <div ref={bannerRef} className="scroll-reveal w-full bg-[#C4161C] py-20 px-6 relative overflow-hidden">
        {/* Background grid */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.2) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
        <div className="max-w-4xl mx-auto text-center relative">
          <div className="flex justify-center gap-1 text-white/80 mb-5">
            {[...Array(5)].map((_, i) => (
              <Star key={i} size={22} className="fill-gold-400 text-gold-400" />
            ))}
          </div>
          <Quote size={40} className="text-white/20 mx-auto mb-4" />
          <h3 className="text-2xl md:text-4xl font-bold text-white font-manrope leading-tight mb-8">
            "SachchaSauda has completely transformed how we trade. What used to take hours of analysis now takes minutes. The platform is fast, reliable, and genuinely transparent on pricing."
          </h3>
          <div className="flex items-center justify-center gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center text-white font-bold text-sm border border-white/30">
              AK
            </div>
            <div className="text-left">
              <div className="text-white font-bold text-base">Arjun Kapoor</div>
              <div className="text-white/70 text-sm">Head of Trading, FinEdge Capital</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Dark Testimonials Section ── */}
      <div className="section-dark py-28 px-6 relative overflow-hidden">
        {/* Subtle blue glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-brand-600/8 rounded-full blur-[120px] pointer-events-none" />
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-5 pointer-events-none"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <div className="max-w-7xl mx-auto relative">

          {/* Header */}
          <div ref={headerRef} className="scroll-reveal mb-12 text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/15 border border-brand-500/30 mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E6B839]" />
              <span className="text-xs font-semibold text-gold-400 uppercase tracking-widest">Testimonials</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight font-manrope mb-4">
              What Our{' '}
              <span className="text-[#E6B839]">Clients Say</span>
            </h2>
            <p className="text-lg text-slate-400 font-light">
              Real feedback from real traders who use SachchaSauda every day.
            </p>
          </div>

          {/* Overall Rating */}
          <div ref={ratingRef} className="scroll-reveal flex flex-col sm:flex-row items-center justify-center gap-6 mb-12 p-6 rounded-2xl bg-white/5 border border-white/10 max-w-lg mx-auto backdrop-blur-sm">
            <div className="text-center">
              <div className="text-5xl font-bold text-white font-manrope">4.9</div>
              <div className="flex justify-center gap-0.5 mt-1">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={14} className="fill-amber-400 text-amber-400" />
                ))}
              </div>
              <div className="text-xs text-slate-400 mt-1">Overall Rating</div>
            </div>
            <div className="w-px h-16 bg-white/10 hidden sm:block" />
            <div className="space-y-1.5">
              {[
                { stars: 5, pct: 82 },
                { stars: 4, pct: 13 },
                { stars: 3, pct: 4 },
                { stars: 2, pct: 1 },
              ].map((row) => (
                <div key={row.stars} className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-4">{row.stars}</span>
                  <Star size={10} className="fill-amber-400 text-amber-400" />
                  <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-400 rounded-full" style={{ width: `${row.pct}%` }} />
                  </div>
                  <span className="text-xs text-slate-400">{row.pct}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Testimonial Cards */}
          <div ref={cardsRef} className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {testimonials.map((t) => (
              <div
                key={t.name}
                className="stagger-child group bg-white/5 border border-white/10 rounded-2xl p-7 flex flex-col gap-5 hover:-translate-y-1 hover:border-[#C4161C]/40 hover:bg-white/8 transition-all duration-300 backdrop-blur-sm"
              >
                {/* Top */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-11 h-11 rounded-full ${t.color} flex items-center justify-center text-white font-bold text-sm shrink-0 border border-white/20`}>
                      {t.avatar}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-white font-manrope">{t.name}</div>
                      <div className="text-xs text-slate-400">{t.role}</div>
                    </div>
                  </div>
                  <span className="text-[10px] font-semibold text-[#C4161C] bg-brand-500/15 border border-brand-500/25 px-2 py-1 rounded-full">
                    {t.market}
                  </span>
                </div>

                {/* Stars */}
                <div className="flex gap-0.5">
                  {[...Array(t.rating)].map((_, i) => (
                    <Star key={i} size={13} className="fill-amber-400 text-amber-400" />
                  ))}
                </div>

                {/* Review */}
                <p className="text-sm text-slate-300 leading-relaxed italic">
                  "{t.review}"
                </p>

                {/* Bottom divider */}
                <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}