"use client";

import { TrendingUp, ArrowDownRight } from "lucide-react";

const ACCOUNTS = [
  { icon: "citi", label: "Family", sub: "···· 0276", val: "$1,546", color: "text-blue-600" },
  { icon: "P", label: "Main", sub: "···· 2425", val: "$2,365", color: "text-purple-600" },
];

const CARDS = [
  { icon: "VISA", label: "Visa Card", val: "$1,546" },
  { icon: "Pay", label: "Apple Pay", val: "$2,365" },
];

const BOTTOM_TABS = [
  { active: true },
  { active: false },
  { active: false },
  { active: false },
  { active: false },
];

export function PhoneMockup() {
  return (
    <div className="relative mx-auto w-[300px] sm:w-[340px]">
      {/* Glow behind phone */}
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-10 -z-10 rounded-[60px] bg-primary/15 blur-[60px]"
      />

      {/* Phone frame — dark border like reference */}
      <div className="relative overflow-hidden rounded-[44px] border-[8px] border-[#1a1a2e] bg-white shadow-2xl shadow-black/20">
        {/* Status bar */}
        <div className="flex items-center justify-between bg-white px-6 pb-1 pt-3">
          <span className="text-xs font-semibold text-gray-900">9:41</span>
          <div className="mx-auto h-[22px] w-[90px] rounded-full bg-[#1a1a2e]" />
          <div className="flex items-center gap-1">
            <div className="h-2.5 w-1 rounded-full bg-gray-400" />
            <div className="h-3 w-1 rounded-full bg-gray-500" />
            <div className="h-3.5 w-1 rounded-full bg-gray-600" />
            <div className="ml-1.5 h-3 w-5 rounded-sm border border-gray-500 bg-gray-500" />
          </div>
        </div>

        {/* App content */}
        <div className="space-y-4 bg-white px-5 pb-6 pt-3">
          {/* Header icon */}
          <div className="flex items-center justify-between">
            <div className="grid size-8 place-items-center rounded-lg bg-gray-100">
              <TrendingUp className="size-4 text-gray-600" />
            </div>
          </div>

          {/* Balance */}
          <div>
            <div className="flex items-center gap-1 text-xs text-gray-500">
              Balance
              <ArrowDownRight className="size-3" />
            </div>
            <div className="mt-0.5 font-tabular text-[32px] font-bold leading-tight tracking-tight text-gray-900">
              $15,786.00
            </div>
          </div>

          {/* Deposit / Withdraw buttons */}
          <div className="flex gap-2.5">
            <button className="flex-1 rounded-xl bg-primary py-2.5 text-[12px] font-semibold text-white">
              Deposit
            </button>
            <button className="flex-1 rounded-xl bg-primary py-2.5 text-[12px] font-semibold text-white">
              Withdraw
            </button>
          </div>

          {/* Bank Accounts */}
          <div>
            <div className="mb-2 text-[11px] font-medium text-gray-400">
              Bank Accounts
            </div>
            <div className="space-y-2">
              {ACCOUNTS.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className={`text-sm font-bold ${item.color}`}>
                      {item.icon}
                    </div>
                    <div>
                      <div className="text-[12px] font-medium text-gray-900">
                        {item.label}
                      </div>
                      <div className="text-[10px] text-gray-400">
                        {item.sub}
                      </div>
                    </div>
                  </div>
                  <div className="font-tabular text-[12px] font-semibold text-gray-900">
                    {item.val}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cards */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-medium text-gray-400">
                Cards
              </span>
              <span className="text-xs text-primary">+</span>
            </div>
            <div className="space-y-2">
              {CARDS.map((card) => (
                <div
                  key={card.label}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-bold text-gray-700">
                      {card.icon}
                    </span>
                    <span className="text-[12px] font-medium text-gray-900">
                      {card.label}
                    </span>
                  </div>
                  <span className="font-tabular text-[12px] font-semibold text-gray-900">
                    {card.val}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom nav dots */}
        <div className="flex items-center justify-center gap-3 border-t border-gray-100 bg-white px-4 py-4">
          {BOTTOM_TABS.map((tab, i) => (
            <div
              key={i}
              className={`size-2 rounded-full ${
                i === 0 ? "bg-gray-800" : "bg-gray-200"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
