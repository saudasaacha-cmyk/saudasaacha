import type { Metadata } from "next";
import { MarketingNav } from "@/components/marketing/MarketingNav";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";

export const metadata: Metadata = {
  title: "SaudaSaacha — Trade Equity, F&O, Commodities & IPOs on NSE, BSE & MCX",
  description:
    "A SEBI-registered stock broker for Indian markets. Trade Equity, F&O, Commodities, IPOs and Mutual Funds with transparent pricing and a modern platform.",
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // `mp-scope` activates the locked SaudaSaacha marketing palette (light
  // default + dark sections) without touching the trading app's tokens.
  return (
    <div className="mp-scope flex min-h-screen flex-col overflow-x-hidden bg-mp-bg text-mp-text">
      <MarketingNav />
      <main className="flex-1">{children}</main>
      <MarketingFooter />
    </div>
  );
}
