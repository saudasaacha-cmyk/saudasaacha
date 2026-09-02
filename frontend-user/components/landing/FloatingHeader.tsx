"use client";

import { Wordmark } from "@/components/layout/Wordmark";
import React from 'react';
import Link from 'next/link';
import { MenuIcon, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const links = [
  { label: 'Home', href: '#home' },
  { label: 'Markets', href: '#services' },
  { label: 'About', href: '#about' },
  { label: 'Services', href: '#services' },
  { label: 'Contact', href: '#contact' },
];

export function FloatingHeader() {
  const [open, setOpen] = React.useState(false);

  return (
    <header
      className={cn(
        'mx-auto w-[92%] max-w-5xl rounded-2xl border border-slate-200/80 shadow-lg',
        'bg-white/90 supports-[backdrop-filter]:bg-white/75 backdrop-blur-lg',
      )}
    >
      <nav className="mx-auto flex items-center justify-between p-2">
        {/* Logo */}
        <Link
          href="#home"
          className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-slate-100 transition-colors"
          aria-label="SaudaSaacha home"
        >
          <Wordmark markClassName="size-7" textClassName="text-xl" className="text-slate-900" />
        </Link>

        {/* Desktop links */}
        <div className="hidden lg:flex items-center gap-1">
          {links.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:text-[#1F4677] hover:bg-slate-100 transition-colors"
            >
              {l.label}
            </a>
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="hidden sm:inline-flex items-center rounded-md px-4 py-2 text-sm font-semibold text-[#1F4677] border border-[#1F4677]/25 hover:bg-[#1F4677]/5 transition-colors"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="btn-gold inline-flex items-center rounded-md px-4 py-2 text-sm font-bold"
          >
            Get Started
          </Link>
          <button
            type="button"
            className="lg:hidden inline-flex items-center justify-center rounded-md p-2 text-[#1F4677] hover:bg-slate-100"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            {open ? <X className="size-5" /> : <MenuIcon className="size-5" />}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      {open && (
        <div className="lg:hidden border-t border-slate-200 px-3 py-3">
          <div className="grid gap-1">
            {links.map((l) => (
              <a
                key={l.label}
                href={l.href}
                onClick={() => setOpen(false)}
                className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              >
                {l.label}
              </a>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <Link
              href="/login"
              onClick={() => setOpen(false)}
              className="flex-1 text-center rounded-md px-4 py-2 text-sm font-semibold text-[#1F4677] border border-[#1F4677]/25 hover:bg-[#1F4677]/5"
            >
              Login
            </Link>
            <Link
              href="/register"
              onClick={() => setOpen(false)}
              className="btn-gold flex-1 text-center rounded-md px-4 py-2 text-sm font-bold"
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

export default FloatingHeader;
