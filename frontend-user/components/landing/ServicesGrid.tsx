"use client";

import Link from 'next/link';
import { TrendingUp, DollarSign, Bitcoin, ArrowRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

const services: { icon: LucideIcon; title: string; desc: string; img: string }[] = [
  { icon: TrendingUp, title: 'Equity & Derivatives', desc: 'NSE & BSE cash, futures and options with deep liquidity and fast fills.', img: '/card1.png' },
  { icon: DollarSign, title: 'Forex & Commodities', desc: 'Major currency pairs, bullion, base metals and energy — tight spreads.', img: '/card2.png' },
  { icon: Bitcoin,    title: 'Crypto & Global Stocks', desc: 'Top digital assets and US-listed names, traded around the clock.', img: '/card3.png' },
];

export default function ServicesGrid() {
  return (
    <section id="services" className="bg-white py-24 md:py-28 px-6 relative overflow-hidden">
      <div className="max-w-7xl mx-auto relative">

        {/* Header */}
        <div className="grid lg:grid-cols-2 gap-8 items-end mb-12">
          <div>
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gold-50 border border-gold-200 mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E6B839]" />
              <span className="text-xs font-semibold text-[#8a621b] uppercase tracking-widest">Our Services</span>
            </span>
            <h2 className="text-3xl md:text-5xl font-bold text-slate-900 font-manrope tracking-tight leading-[1.1]">
              Markets To Grow And{' '}
              <span className="text-[#C4161C] gold-underline">Secure Your Wealth</span>
            </h2>
          </div>
          <div className="lg:pb-2">
            <p className="text-base text-slate-500 leading-relaxed mb-5">
              Access every major Indian and global market from a single account, with honest
              pricing, instant funding and bank-grade security on every trade.
            </p>
            <Link
              href="/register"
              className="btn-gold inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold"
            >
              Learn More
              <ArrowRight size={15} />
            </Link>
          </div>
        </div>

        {/* Service image cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {services.map((s) => {
            const Icon = s.icon;
            return (
              <div
                key={s.title}
                className="relative rounded-3xl overflow-hidden h-[380px] group border border-slate-200 premium-shadow"
              >
                {/* Background image */}
                <img
                  src={s.img}
                  alt={s.title}
                  className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />

                {/* Bottom overlay */}
                <div
                  className="absolute inset-x-0 bottom-0 p-6 pt-16"
                  style={{ background: 'linear-gradient(to top, #0d0d0d 0%, rgba(15,34,56,0.92) 55%, transparent 100%)' }}
                >
                  <div className="w-12 h-12 rounded-full bg-[#E6B839] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Icon size={22} className="text-[#C4161C]" />
                  </div>
                  <h3 className="text-xl font-bold text-white font-manrope mb-1.5">{s.title}</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
