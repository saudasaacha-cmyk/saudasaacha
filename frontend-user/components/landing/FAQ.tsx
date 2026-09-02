"use client";

import { useState } from 'react';
import { ChevronDown, HelpCircle, MessageCircle, Phone, Mail } from 'lucide-react';
import { useScrollAnimation } from './hooks/useScrollAnimation';

const faqs = [
  {
    q: 'What documents are required to open an account?',
    a: 'You need a valid PAN card, Aadhaar card, a bank account with cancelled cheque or bank statement, and a passport-size photograph. The entire process is digital and takes less than 10 minutes.',
  },
  {
    q: 'Is there any brokerage charge?',
    a: 'SachchaSauda keeps brokerage simple and transparent — a flat fee of ₹20 per order for intraday and F&O trades, regardless of trade size. No hidden charges, ever.',
  },
  {
    q: 'How can I withdraw funds?',
    a: 'Fund withdrawals are processed instantly to your registered bank account. Simply go to the Funds section, enter the withdrawal amount, and confirm. Funds are credited within 24 hours on working days.',
  },
  {
    q: 'Is trading safe on your platform?',
    a: 'Absolutely. We use 256-bit SSL encryption and two-factor authentication (2FA). Your funds are held in a separate client account and are never used for any other purpose.',
  },
  {
    q: 'How long does account verification take?',
    a: 'Account verification is typically completed within 24 hours on working days. With our instant KYC process using Aadhaar OTP, many accounts are verified in under 10 minutes.',
  },
  {
    q: 'Can I trade on mobile?',
    a: 'Yes! Our mobile app is available on both Android (Google Play) and iOS (App Store). It offers the full trading experience including charts, order placement, portfolio tracking, and fund management.',
  },
  {
    q: 'What markets can I trade on SachchaSauda?',
    a: 'You can trade NSE & BSE equities, derivatives (F&O), commodities (MCX), forex currency pairs, US stocks & ETFs, and cryptocurrencies — all from a single unified account.',
  },
  {
    q: 'Is there a minimum deposit requirement?',
    a: 'There is no minimum deposit to open an account. However, you need sufficient margin in your account to place trades. For equity delivery, you can start with as little as ₹100.',
  },
];

interface FAQItemProps {
  faq: { q: string; a: string };
  isOpen: boolean;
  onToggle: () => void;
}

function FAQItem({ faq, isOpen, onToggle }: FAQItemProps) {
  return (
    <div
      className={`border rounded-2xl overflow-hidden transition-all duration-300 ${
        isOpen ? 'border-[#C4161C] bg-brand-50/30' : 'border-slate-200 bg-white hover:border-brand-200'
      }`}
    >
      <button
        className="w-full flex items-center justify-between px-5 py-4 text-left gap-4"
        onClick={onToggle}
      >
        <span className={`text-sm font-semibold font-manrope transition-colors ${isOpen ? 'text-[#C4161C]' : 'text-slate-800'}`}>
          {faq.q}
        </span>
        <ChevronDown
          size={16}
          className={`shrink-0 transition-all duration-300 ${isOpen ? 'rotate-180 text-[#C4161C]' : 'text-slate-400'}`}
        />
      </button>
      <div
        className="overflow-hidden"
        style={{
          maxHeight: isOpen ? '200px' : '0',
          opacity: isOpen ? 1 : 0,
          transition: 'max-height 0.4s ease, opacity 0.3s ease',
        }}
      >
        <div className="px-5 pb-4">
          <div className="h-px bg-brand-100 mb-3" />
          <p className="text-sm text-slate-600 leading-relaxed">{faq.a}</p>
        </div>
      </div>
    </div>
  );
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState(0);
  const { ref: headerRef } = useScrollAnimation();
  const { ref: leftRef } = useScrollAnimation(0.1);
  const { ref: rightRef } = useScrollAnimation(0.1);

  return (
    <section className="py-28 px-6 bg-white relative overflow-hidden">
      {/* Decorative */}
      <div className="absolute top-0 left-0 w-72 h-72 bg-brand-500/4 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto">

        {/* Header */}
        <div ref={headerRef} className="scroll-reveal mb-16 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gold-50 border border-gold-200 mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#E6B839]" />
            <span className="text-xs font-semibold text-[#8a621b] uppercase tracking-widest">FAQ</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight font-manrope mb-4">
            Frequently Asked{' '}
            <span className="text-[#C4161C] gold-underline">Questions</span>
          </h2>
          <p className="text-lg text-slate-500 font-light">
            Everything you need to know about SachchaSauda.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">

          {/* LEFT — FAQ accordion (2/3 width) */}
          <div ref={leftRef} className="scroll-reveal-left lg:col-span-2 space-y-3">
            {faqs.map((faq, i) => (
              <FAQItem
                key={i}
                faq={faq}
                isOpen={openIndex === i}
                onToggle={() => setOpenIndex(openIndex === i ? -1 : i)}
              />
            ))}
          </div>

          {/* RIGHT — Help card (1/3 width) */}
          <div ref={rightRef} className="scroll-reveal-right flex flex-col gap-5">

            {/* Still have questions card */}
            <div className="bg-[#C4161C] rounded-2xl p-7 text-white relative overflow-hidden">
              {/* Pattern */}
              <div
                className="absolute inset-0 opacity-10 pointer-events-none"
                style={{
                  backgroundImage: 'linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)',
                  backgroundSize: '24px 24px',
                }}
              />
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-white/20 border border-white/30 flex items-center justify-center mb-5">
                  <HelpCircle size={22} className="text-white" />
                </div>
                <h3 className="text-lg font-bold font-manrope mb-2">More Questions?</h3>
                <p className="text-brand-100 text-sm leading-relaxed mb-6">
                  Our support team is available 24/7 to help you with any queries about trading, accounts, or funds.
                </p>
                <a
                  href="#contact"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-white text-[#C4161C] text-sm font-bold hover:bg-brand-50 transition-all"
                >
                  Contact Support
                </a>
              </div>
            </div>

            {/* Quick contact options */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
              <div className="text-sm font-bold text-slate-700 font-manrope mb-2">Reach us directly</div>
              {[
                { icon: Phone, label: 'Phone Support', value: '+91 98765 43210', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
                { icon: Mail, label: 'Email Support', value: 'support@sachchasauda.com', color: 'text-brand-600', bg: 'bg-brand-50', border: 'border-brand-100' },
                { icon: MessageCircle, label: 'Live Chat', value: 'Available 24/7', color: 'text-[#C4161C]', bg: 'bg-brand-50', border: 'border-brand-100' },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl ${item.bg} border ${item.border} flex items-center justify-center shrink-0`}>
                      <Icon size={15} className={item.color} />
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">{item.label}</div>
                      <div className="text-sm font-semibold text-slate-800">{item.value}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Response time badge */}
            <div className="flex items-center gap-3 p-4 rounded-2xl bg-emerald-50 border border-emerald-100">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
              </span>
              <div>
                <div className="text-xs font-bold text-emerald-700">Average Response Time</div>
                <div className="text-sm font-bold text-emerald-800 font-manrope">Under 2 minutes</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}