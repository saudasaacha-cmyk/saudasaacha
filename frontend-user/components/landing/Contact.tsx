"use client";

import { Phone, Mail, MessageCircle, MessageSquare, MapPin, Clock, ArrowRight, Send } from 'lucide-react';
import { useState } from 'react';
import { useScrollAnimation, useStaggerAnimation } from './hooks/useScrollAnimation';
import ImageBox from './ImageBox';

const contactMethods = [
  {
    icon: Phone,
    title: 'Phone Support',
    desc: 'Talk to our trading experts directly',
    value: '+91 1800-123-4567',
    sub: 'Mon–Sat, 9AM–6PM IST',
    color: 'text-[#C4161C]',
    bg: 'bg-brand-50',
    border: 'border-brand-100',
    action: 'Call Now',
  },
  {
    icon: Mail,
    title: 'Email Support',
    desc: 'Get detailed answers to your queries',
    value: 'support@sachchasauda.com',
    sub: 'Response within 2 hours',
    color: 'text-[#C4161C]',
    bg: 'bg-brand-50',
    border: 'border-brand-100',
    action: 'Send Email',
  },
  {
    icon: MessageCircle,
    title: 'Live Chat',
    desc: 'Instant help from our support team',
    value: 'Chat with us now',
    sub: 'Available 24/7',
    color: 'text-[#C4161C]',
    bg: 'bg-brand-50',
    border: 'border-brand-100',
    action: 'Start Chat',
  },
  {
    icon: MessageSquare,
    title: 'WhatsApp',
    desc: 'Quick support on WhatsApp',
    value: '+91 98765 43210',
    sub: 'Mon–Sat, 9AM–9PM IST',
    color: 'text-[#C4161C]',
    bg: 'bg-brand-50',
    border: 'border-brand-100',
    action: 'Message Us',
  },
];

export default function Contact() {
  const [formData, setFormData] = useState({ name: '', email: '', subject: '', message: '' });
  const [submitted, setSubmitted] = useState(false);
  const { ref: headerRef } = useScrollAnimation();
  const cardsRef           = useStaggerAnimation(0.08, 80);
  const { ref: formRef }   = useScrollAnimation(0.1);
  const { ref: infoRef }   = useScrollAnimation(0.1);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  };

  return (
    <section id="contact" className="py-24 md:py-28 px-6 bg-[#f7f9fc] relative overflow-hidden">
      <div className="absolute bottom-0 left-0 w-72 h-72 bg-brand-500/4 rounded-full blur-[100px] pointer-events-none" />
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div ref={headerRef} className="scroll-reveal mb-16 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gold-50 border border-gold-200 mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#E6B839]" />
            <span className="text-xs font-semibold text-[#8a621b] uppercase tracking-widest">Contact Us</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight font-manrope mb-4">
            Need Help? Contact Our{' '}
            <span className="text-[#C4161C] gold-underline">Support Team</span>
          </h2>
          <p className="text-lg text-slate-500 font-light">
            We're here to help you 24/7. Reach out through any channel that works best for you.
          </p>
        </div>

        {/* Contact Method Cards */}
        <div ref={cardsRef} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-16">
          {contactMethods.map((method) => {
            const Icon = method.icon;
            return (
              <div key={method.title} className="stagger-child card-light group p-6 flex flex-col gap-4">
                <div className={`w-12 h-12 rounded-2xl ${method.bg} border ${method.border} flex items-center justify-center group-hover:scale-110 group-hover:bg-[#C4161C] group-hover:border-[#C4161C] transition-all`}>
                  <Icon size={22} className={`${method.color} group-hover:text-white transition-colors`} />
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900 font-manrope mb-0.5">{method.title}</div>
                  <div className="text-xs text-slate-400 mb-3">{method.desc}</div>
                  <div className={`text-sm font-semibold ${method.color}`}>{method.value}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <Clock size={10} className="text-slate-400" />
                    <span className="text-[10px] text-slate-400">{method.sub}</span>
                  </div>
                </div>
                <button className={`mt-auto flex items-center gap-1.5 text-xs font-bold ${method.color} group-hover:gap-2.5 transition-all`}>
                  {method.action} <ArrowRight size={12} />
                </button>
              </div>
            );
          })}
        </div>

        {/* Contact Form + Office Info */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form */}
          <div ref={formRef} className="scroll-reveal-left lg:col-span-2 soft-card rounded-3xl premium-shadow p-8">
            <div className="text-lg font-bold text-slate-900 font-manrope mb-6">Send Us a Message</div>

            {submitted ? (
              <div className="flex flex-col items-center justify-center py-12 gap-4">
                <div className="w-16 h-16 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center">
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <path d="M6 14l6 6 10-12" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div className="text-base font-bold text-slate-900 font-manrope">Message Sent!</div>
                <div className="text-sm text-slate-500">We'll get back to you within 2 hours.</div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-500 mb-1.5 block">Your Name</label>
                    <input
                      type="text"
                      placeholder="Rahul Sharma"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-500 mb-1.5 block">Email Address</label>
                    <input
                      type="email"
                      placeholder="rahul@example.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-500 mb-1.5 block">Subject</label>
                  <select
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all"
                    required
                  >
                    <option value="">Select a topic</option>
                    <option>Account Opening</option>
                    <option>Fund Deposit / Withdrawal</option>
                    <option>Technical Issue</option>
                    <option>Trading Query</option>
                    <option>Other</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-500 mb-1.5 block">Message</label>
                  <textarea
                    rows={5}
                    placeholder="Describe your query in detail..."
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 text-sm focus:outline-none focus:border-[#C4161C] focus:bg-white transition-all resize-none"
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-4 rounded-xl bg-[#C4161C] text-white font-bold text-sm hover:bg-brand-800 transition-all shadow-lg shadow-brand-100 flex items-center justify-center gap-2"
                >
                  <Send size={16} />
                  Send Message
                </button>
              </form>
            )}
          </div>

          {/* Office Info */}
          <div ref={infoRef} className="scroll-reveal-right flex flex-col gap-5">
            {/* Office Card */}
            <div className="soft-card rounded-3xl p-6 hover:-translate-y-1 hover:border-brand-200 transition-all duration-300">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-brand-50 border border-brand-100 flex items-center justify-center">
                  <MapPin size={18} className="text-[#C4161C]" />
                </div>
                <div className="text-sm font-bold text-slate-900 font-manrope">Our Office</div>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed">
                SaudaSaacha<br />
                14th Floor, Infinity Tower,<br />
                Bandra Kurla Complex,<br />
                Mumbai – 400 051, Maharashtra
              </p>
            </div>

            {/* Map placeholder */}
            <ImageBox
              ratio="auto"
              label="Office Location"
              sublabel="Bandra Kurla Complex, Mumbai"
              icon={MapPin}
              className="h-44"
            />

            {/* Hours Card */}
            <div className="soft-card rounded-3xl p-6 hover:-translate-y-1 hover:border-brand-200 transition-all duration-300">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-brand-50 border border-brand-100 flex items-center justify-center">
                  <Clock size={18} className="text-[#C4161C]" />
                </div>
                <div className="text-sm font-bold text-slate-900 font-manrope">Support Hours</div>
              </div>
              <div className="space-y-2">
                {[
                  { day: 'Monday – Friday', time: '9:00 AM – 6:00 PM' },
                  { day: 'Saturday', time: '9:00 AM – 2:00 PM' },
                  { day: 'Sunday', time: 'Closed' },
                  { day: 'Live Chat', time: '24 / 7' },
                ].map((row) => (
                  <div key={row.day} className="flex justify-between text-xs">
                    <span className="text-slate-500">{row.day}</span>
                    <span className={`font-semibold ${row.time === 'Closed' ? 'text-red-400' : row.time === '24 / 7' ? 'text-emerald-600' : 'text-slate-700'}`}>
                      {row.time}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}