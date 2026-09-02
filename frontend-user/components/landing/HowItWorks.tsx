"use client";

import Link from 'next/link';
import { BadgePercent, Zap, Layers, ArrowRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

const services: { icon: LucideIcon; title: string; desc: string }[] = [
  { icon: BadgePercent, title: 'Transparent Pricing', desc: 'Flat, transparent pricing across every segment — no hidden platform or inactivity fees.' },
  { icon: Zap,          title: 'Instant Execution',  desc: 'Ultra-low-latency order matching so your trades fill the moment you place them.' },
  { icon: Layers,       title: 'Multi-Asset Access',  desc: 'Equities, F&O, commodities, forex, US stocks and crypto from one single account.' },
];

export default function HowItWorks() {
  return (
    <section className="relative bg-[#f7f9fc] px-6 pt-20 pb-24">
      <div className="max-w-7xl mx-auto grid lg:grid-cols-[330px_1fr] gap-6">

        {/* Left — "How Does It Work?" image card */}
        <div className="relative rounded-3xl overflow-hidden min-h-[260px] p-6 flex flex-col justify-end border border-white/10 premium-shadow">
          {/* Background image */}
          <img
            src="/image1.png"
            alt="How SaudaSaacha works"
            className="absolute inset-0 w-full h-full object-cover"
          />
          {/* Dark gradient overlay so the heading + link stay readable over the photo */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#0d0d0d] via-[#0d0d0d]/70 to-[#0d0d0d]/10" />
          <div className="relative">
            <h3 className="text-white text-2xl font-bold font-manrope mb-2">How Does It Work?</h3>
            <Link href="/register" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#E6B839] hover:gap-2.5 transition-all">
              Learn More <ArrowRight size={14} />
            </Link>
          </div>
        </div>

        {/* Right — dark panel with 3 service columns */}
        <div className="rounded-3xl p-8 md:p-10 grid sm:grid-cols-3 gap-8 premium-shadow"
          style={{ background: 'linear-gradient(135deg, #C4161C 0%, #1a1a1a 100%)' }}
        >
          {services.map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.title} className="group">
                <div className="w-12 h-12 rounded-full bg-[#E6B839] flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <Icon size={22} className="text-[#C4161C]" />
                </div>
                <h3 className="text-white text-lg font-bold font-manrope mb-2 leading-snug">{s.title}</h3>
                <p className="text-sm text-slate-300 leading-relaxed">{s.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
