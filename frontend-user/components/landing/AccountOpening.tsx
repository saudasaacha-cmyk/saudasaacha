"use client";

import { CheckCircle2, Zap, Shield, Clock, ArrowRight, Smartphone, CreditCard, Building2 } from 'lucide-react';
import Link from 'next/link';
import { useScrollAnimation, useStaggerAnimation } from './hooks/useScrollAnimation';
import ImageBox from './ImageBox';

const benefits = [
  { icon: Zap,          text: 'Instant digital KYC verification',    color: 'text-[#C4161C]', bg: 'bg-brand-50',  border: 'border-brand-100' },
  { icon: Shield,       text: 'Bank-grade security & encryption',     color: 'text-[#C4161C]', bg: 'bg-brand-50',  border: 'border-brand-100' },
  { icon: Clock,        text: 'Account active in under 10 minutes',   color: 'text-[#C4161C]', bg: 'bg-brand-50',  border: 'border-brand-100' },
  { icon: CheckCircle2, text: 'Zero account opening charges',         color: 'text-[#C4161C]', bg: 'bg-brand-50',  border: 'border-brand-100' },
];

const paymentMethods = [
  { icon: Smartphone,  label: 'UPI',         sub: 'Instant transfer',  color: 'text-[#C4161C]', bg: 'bg-brand-50', border: 'border-brand-100' },
  { icon: Building2,   label: 'Net Banking', sub: 'All major banks',   color: 'text-[#C4161C]', bg: 'bg-brand-50', border: 'border-brand-100' },
  { icon: CreditCard,  label: 'Debit Card',  sub: 'Visa / Mastercard', color: 'text-[#C4161C]', bg: 'bg-brand-50', border: 'border-brand-100' },
];

const steps = [
  {
    step: '01',
    title: 'Register Your Account',
    desc: 'Enter your mobile number, email, and basic details. Verify with OTP in seconds.',
    color: 'text-[#C4161C]',
    bg: 'bg-brand-50',
    border: 'border-brand-200',
  },
  {
    step: '02',
    title: 'Add Funds Securely',
    desc: 'Deposit funds via UPI, Net Banking, or Debit Card. Instant credit to your trading account.',
    color: 'text-[#C4161C]',
    bg: 'bg-brand-50',
    border: 'border-brand-200',
  },
  {
    step: '03',
    title: 'Start Trading Instantly',
    desc: 'Access all markets, place your first trade, and start building your portfolio right away.',
    color: 'text-[#C4161C]',
    bg: 'bg-[#C4161C]',
    border: 'border-[#C4161C]',
  },
];

export default function AccountOpening() {
  const { ref: leftRef }   = useScrollAnimation(0.1);
  const { ref: rightRef }  = useScrollAnimation(0.1);
  const { ref: stepsHdr }  = useScrollAnimation(0.1);
  const stepsRef           = useStaggerAnimation(0.1, 120);
  const { ref: ctaRef }    = useScrollAnimation(0.1);

  return (
    <section id="account" className="py-24 md:py-28 px-6 bg-white relative overflow-hidden">
      <div className="absolute top-0 right-0 w-80 h-80 bg-brand-500/4 rounded-full blur-[100px] pointer-events-none" />
      <div className="max-w-7xl mx-auto">

        {/* Top: Account Opening CTA */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center mb-24">
          {/* Left */}
          <div ref={leftRef} className="scroll-reveal-left">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gold-50 border border-gold-200 mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E6B839]" />
              <span className="text-xs font-semibold text-[#8a621b] uppercase tracking-widest">Get Started</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight font-manrope mb-5 leading-tight">
              Open Your Account in{' '}
              <span className="text-[#C4161C] gold-underline">Under 10 Seconds</span>
            </h2>
            <p className="text-lg text-slate-500 mb-8 leading-relaxed">
              Simple digital onboarding with instant verification and secure KYC process.
              No paperwork, no branch visits — 100% online.
            </p>

            {/* Benefits */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
              {benefits.map((b) => {
                const Icon = b.icon;
                return (
                  <div key={b.text} className={`flex items-center gap-3 p-3 rounded-2xl ${b.bg} border ${b.border} hover:-translate-y-1 hover:border-brand-200 transition-all duration-300`}>
                    <Icon size={16} className={b.color} />
                    <span className="text-sm text-slate-700 font-medium">{b.text}</span>
                  </div>
                );
              })}
            </div>

            {/* Payment Methods */}
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Supported Payment Methods:</p>
              <div className="flex gap-3">
                {paymentMethods.map((pm) => {
                  const Icon = pm.icon;
                  return (
                    <div key={pm.label} className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl border ${pm.border} ${pm.bg} hover:-translate-y-1 hover:border-brand-200 transition-all duration-300`}>
                      <Icon size={16} className={pm.color} />
                      <div>
                        <div className="text-xs font-bold text-slate-800">{pm.label}</div>
                        <div className="text-[10px] text-slate-400">{pm.sub}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right: Form Card */}
          <div ref={rightRef} className="scroll-reveal-right soft-card rounded-3xl premium-shadow p-8">
            <div className="text-center mb-6">
              <div className="text-xl font-bold text-slate-900 font-manrope mb-1">Create Free Account</div>
              <div className="text-sm text-slate-400">Join 150,000+ traders today</div>
            </div>

            <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-500 mb-1.5 block">First Name</label>
                  <input
                    type="text"
                    placeholder="Rahul"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 mb-1.5 block">Last Name</label>
                  <input
                    type="text"
                    placeholder="Sharma"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 mb-1.5 block">Mobile Number</label>
                <div className="flex gap-2">
                  <div className="px-3 py-3 rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-600 font-medium">+91</div>
                  <input
                    type="tel"
                    placeholder="9876543210"
                    className="flex-1 px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 mb-1.5 block">Email Address</label>
                <input
                  type="email"
                  placeholder="rahul@example.com"
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 mb-1.5 block">PAN Number</label>
                <input
                  type="text"
                  placeholder="ABCDE1234F"
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all uppercase"
                />
              </div>

              <Link
                href="/register"
                className="w-full py-4 rounded-xl bg-[#C4161C] text-white font-bold text-sm hover:bg-brand-800 transition-all shadow-lg shadow-brand-100 flex items-center justify-center gap-2 glow-btn"
              >
                Open Free Account
                <ArrowRight size={16} />
              </Link>

              <p className="text-center text-[11px] text-slate-400">
                By registering, you agree to our{' '}
                <Link href="/terms" className="text-[#C4161C] hover:underline">Terms & Conditions</Link>{' '}
                and{' '}
                <Link href="/privacy-policy" className="text-[#C4161C] hover:underline">Privacy Policy</Link>
              </p>
            </form>
          </div>
        </div>

        {/* Onboarding mockup */}
        <div className="max-w-5xl mx-auto mb-16">
          <ImageBox
            ratio="wide"
            src="/image3.png"
            alt="Onboarding in minutes — KYC, fund and trade, fully digital"
            className="premium-shadow"
          />
        </div>

        {/* 3 Steps Section */}
        <div ref={stepsHdr} className="scroll-reveal text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-bold text-slate-900 tracking-tight font-manrope mb-3">
            Start Trading in{' '}
            <span className="text-[#C4161C] gold-underline">3 Easy Steps</span>
          </h2>
          <p className="text-slate-500">Simple, fast, and completely digital.</p>
        </div>

        <div ref={stepsRef} className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
          {/* Connector line */}
          <div className="hidden md:block absolute top-12 left-1/3 right-1/3 h-px bg-gradient-to-r from-brand-200 via-brand-300 to-brand-200" />

          {steps.map((step, i) => (
            <div key={step.step} className="stagger-child card-light p-8 text-center flex flex-col items-center gap-4 relative">
              {/* Step number */}
              <div className={`w-16 h-16 rounded-2xl ${i === 2 ? 'bg-[#C4161C]' : step.bg} border ${step.border} flex items-center justify-center`}>
                <span className={`text-2xl font-bold font-manrope ${i === 2 ? 'text-white' : step.color}`}>{step.step}</span>
              </div>

              <h3 className="text-lg font-bold text-slate-900 font-manrope">{step.title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{step.desc}</p>

              {/* Arrow between steps */}
              {i < steps.length - 1 && (
                <div className="md:hidden flex justify-center mt-2">
                  <ArrowRight size={20} className="text-slate-300 rotate-90" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Final CTA */}
        <div ref={ctaRef} className="scroll-reveal mt-12 text-center">
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-10 py-4 rounded-full bg-[#C4161C] text-white font-bold text-base hover:bg-brand-800 transition-all shadow-xl shadow-brand-100 hover:shadow-brand-200 glow-btn"
          >
            Create Account Now
            <ArrowRight size={18} />
          </Link>
          <p className="text-xs text-slate-400 mt-3">Free forever · No credit card required · Instant activation</p>
        </div>
      </div>
    </section>
  );
}