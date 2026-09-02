"use client";

import Link from 'next/link';
import { Target, Compass, CheckCircle2, ArrowRight } from 'lucide-react';
import ImageBox from './ImageBox';

const stats = [
  { value: '1M+',   label: 'Orders processed every single month.' },
  { value: '150K+', label: 'Active traders growing across India.' },
  { value: '99.9%', label: 'Uptime you can rely on, every session.' },
  { value: '₹5M+',  label: 'Daily trading volume settled securely.' },
];

export default function AboutStats() {
  return (
    <section id="about" className="bg-white py-24 md:py-28 px-6 relative overflow-hidden">
      <div className="absolute top-20 right-0 w-72 h-72 bg-gold-400/8 rounded-full blur-[110px] pointer-events-none" />
      <div className="max-w-7xl mx-auto relative">

        {/* About grid */}
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">

          {/* Left — image + Company Vision */}
          <div>
            <ImageBox
              ratio="auto"
              variant="light"
              src="/image2.png"
              alt="The SaudaSaacha team at work"
              className="w-full h-[300px] md:h-[360px] premium-shadow"
            />
            <div className="mt-8 flex items-start gap-4">
              <div className="w-12 h-12 rounded-full bg-[#1F4677] flex items-center justify-center shrink-0">
                <Compass size={22} className="text-[#E6B839]" />
              </div>
              <div>
                <h4 className="text-lg font-bold text-slate-900 font-manrope mb-1">Company Vision</h4>
                <p className="text-sm text-slate-500 leading-relaxed max-w-sm">
                  To make professional-grade, multi-market trading accessible and transparent
                  for every Indian — without the legacy fees and friction.
                </p>
              </div>
            </div>
          </div>

          {/* Right — about copy + mission + banner */}
          <div>
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gold-50 border border-gold-200 mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E6B839]" />
              <span className="text-xs font-semibold text-[#8a621b] uppercase tracking-widest">About Us</span>
            </span>

            <h2 className="text-3xl md:text-5xl font-bold text-slate-900 font-manrope tracking-tight leading-[1.1] mb-8">
              India&apos;s Modern{' '}
              <span className="text-[#1F4677] gold-underline">Multi-Market Broker</span>
            </h2>

            <div className="flex items-start gap-4 mb-8">
              <div className="w-12 h-12 rounded-full bg-[#1F4677] flex items-center justify-center shrink-0">
                <Target size={22} className="text-[#E6B839]" />
              </div>
              <div>
                <h4 className="text-lg font-bold text-slate-900 font-manrope mb-1">Company Mission</h4>
                <p className="text-sm text-slate-500 leading-relaxed">
                  Give traders one fast, secure platform for every asset class — equities, F&amp;O,
                  commodities, forex, US stocks and crypto — with honest pricing and instant
                  withdrawals they can trust.
                </p>
              </div>
            </div>

            {/* Dark CTA banner */}
            <div
              className="flex flex-col sm:flex-row items-center gap-4 rounded-2xl px-6 py-5 premium-shadow"
              style={{ background: 'linear-gradient(135deg, #1F4677 0%, #16314f 100%)' }}
            >
              <div className="flex items-start gap-3 flex-1">
                <CheckCircle2 size={20} className="text-[#E6B839] shrink-0 mt-0.5" />
                <p className="text-sm text-slate-200 leading-relaxed">
                  Join us to grow your portfolio and reach your financial goals with the
                  right markets and the right tools.
                </p>
              </div>
              <Link
                href="/register"
                className="btn-gold shrink-0 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold"
              >
                Learn More
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-12 mt-20 pt-14 border-t border-slate-100">
          {stats.map((s) => (
            <div key={s.value}>
              <div className="w-10 h-1.5 rounded-full bg-[#E6B839] mb-5" />
              <div className="flex items-start">
                <span className="text-4xl md:text-5xl font-bold text-[#1F4677] font-manrope leading-none">
                  {s.value}
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-3 leading-relaxed max-w-[180px]">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
