"use client";

import { TrendingUp, TrendingDown, IndianRupee } from "lucide-react";
import { BrandGlyph } from "@/components/layout/BrandGlyph";

const ORBIT_SLOW = [
  { sym: "NIFTY 50",  val: "22,841.55", chg: "+0.42%", dir: "up" },
  { sym: "SENSEX",    val: "75,238.10", chg: "+0.31%", dir: "up" },
  { sym: "BANKNIFTY", val: "48,612.20", chg: "-0.18%", dir: "down" },
  { sym: "FINNIFTY",  val: "21,544.85", chg: "+0.22%", dir: "up" },
];
const ORBIT_MID = [
  { sym: "RELIANCE", val: "2,941.30", chg: "+1.24%", dir: "up" },
  { sym: "TCS",      val: "4,082.65", chg: "-0.46%", dir: "down" },
  { sym: "HDFCBANK", val: "1,648.90", chg: "+0.71%", dir: "up" },
  { sym: "INFY",     val: "1,495.20", chg: "+0.18%", dir: "up" },
  { sym: "ICICIBANK",val: "1,142.75", chg: "+0.55%", dir: "up" },
];
const ORBIT_FAST = [
  { sym: "GOLD",   val: "73,420", chg: "+0.62%", dir: "up" },
  { sym: "CRUDE",  val: "6,512",  chg: "-1.04%", dir: "down" },
  { sym: "USDINR", val: "83.42",  chg: "+0.05%", dir: "up" },
  { sym: "BTCINR", val: "58.2L",  chg: "+2.31%", dir: "up" },
];

function placeOnRing(index: number, total: number, radius: number) {
  const angle = (360 / total) * index;
  return {
    transform: `rotate(${angle}deg) translate(${radius}px) rotate(-${angle}deg)`,
  } as const;
}

function TickerCard({
  sym,
  val,
  chg,
  dir,
  size = "md",
}: {
  sym: string;
  val: string;
  chg: string;
  dir: "up" | "down";
  size?: "sm" | "md";
}) {
  const up = dir === "up";
  return (
    <div
      className={
        "flex select-none items-center gap-2 whitespace-nowrap rounded-lg border border-border/80 bg-card/95 px-2.5 py-1.5 shadow-lg shadow-primary/5 backdrop-blur-md " +
        (size === "sm" ? "text-[10px]" : "text-[11px]")
      }
    >
      <span
        className={
          "grid place-items-center rounded-md " +
          (up ? "bg-buy/15 text-buy" : "bg-sell/15 text-sell") +
          (size === "sm" ? " size-4" : " size-5")
        }
      >
        {up ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
      </span>
      <span className="font-semibold tracking-tight text-foreground">{sym}</span>
      <span className="font-tabular text-muted-foreground">{val}</span>
      <span
        className={
          "font-tabular font-semibold " + (up ? "text-buy" : "text-sell")
        }
      >
        {chg}
      </span>
    </div>
  );
}

export function HeroAnimation() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[640px]">
      {/* Perspective grid backdrop */}
      <div
        aria-hidden
        className="mp-grid-pan absolute inset-0 -z-10 rounded-full opacity-50 [mask-image:radial-gradient(circle_at_center,black_30%,transparent_75%)]"
        style={{
          backgroundImage:
            "linear-gradient(to right, hsl(var(--primary)/0.18) 1px, transparent 1px), linear-gradient(to bottom, hsl(var(--primary)/0.18) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* Radial colour wash — subtle tricolour nod */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(circle at 20% 25%, rgba(255,153,51,0.10), transparent 45%)," +
            "radial-gradient(circle at 80% 75%, rgba(19,136,8,0.10), transparent 45%)," +
            "radial-gradient(circle at 50% 50%, hsl(var(--primary)/0.18), transparent 60%)",
        }}
      />

      {/* Beams */}
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        {[0, 60, 120].map((deg) => (
          <div
            key={deg}
            className="absolute h-px w-[70%] origin-center bg-gradient-to-r from-transparent via-primary/60 to-transparent mp-beam"
            style={{ transform: `rotate(${deg}deg)` }}
          />
        ))}
        <div className="absolute h-px w-[70%] origin-center bg-gradient-to-r from-transparent via-primary/40 to-transparent mp-beam mp-beam-delay-2" />
      </div>

      {/* Outer pulse rings */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="absolute size-[68%] rounded-full border border-primary/30 mp-pulse-ring" />
        <div className="absolute size-[68%] rounded-full border border-primary/30 mp-pulse-ring mp-pulse-ring-delay-1" />
        <div className="absolute size-[68%] rounded-full border border-primary/30 mp-pulse-ring mp-pulse-ring-delay-2" />
      </div>

      {/* Concentric ring tracks (static) */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="absolute size-[88%] rounded-full border border-dashed border-border/60" />
        <div className="absolute size-[64%] rounded-full border border-dashed border-border/60" />
        <div className="absolute size-[42%] rounded-full border border-dashed border-border/60" />
      </div>

      {/* SLOW orbit — indices */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="relative size-[88%] mp-orbit-slow">
          {ORBIT_SLOW.map((t, i) => (
            <div
              key={t.sym}
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
              style={placeOnRing(i, ORBIT_SLOW.length, 240)}
            >
              <div className="mp-orbit-counter-slow">
                <TickerCard {...t} dir={t.dir as "up" | "down"} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MID orbit — large caps */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="relative size-[64%] mp-orbit-mid">
          {ORBIT_MID.map((t, i) => (
            <div
              key={t.sym}
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
              style={placeOnRing(i, ORBIT_MID.length, 180)}
            >
              <div className="mp-orbit-counter-mid">
                <TickerCard {...t} dir={t.dir as "up" | "down"} size="sm" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* FAST orbit — commodities/currency/crypto */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="relative size-[42%] mp-orbit-fast">
          {ORBIT_FAST.map((t, i) => (
            <div
              key={t.sym}
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
              style={placeOnRing(i, ORBIT_FAST.length, 120)}
            >
              <div className="mp-orbit-counter-fast">
                <TickerCard {...t} dir={t.dir as "up" | "down"} size="sm" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Core */}
      <div className="absolute inset-0 grid place-items-center">
        <div className="relative grid size-32 place-items-center rounded-full bg-gradient-to-br from-primary via-primary/80 to-primary/60 shadow-[0_0_60px_rgba(120,90,240,0.55)]">
          <div className="absolute inset-0 rounded-full mp-shimmer" />
          <div className="absolute -inset-1.5 -z-10 rounded-full bg-primary/30 blur-2xl mp-spark" />
          <div className="relative grid size-28 place-items-center rounded-full bg-[#0a0a0a] backdrop-blur-sm">
            <BrandGlyph className="size-12 text-white drop-shadow" />
          </div>
          <span className="absolute -bottom-7 rounded-full border border-primary/30 bg-background/80 px-2.5 py-0.5 text-[10px] font-semibold tracking-wider text-primary backdrop-blur">
            SAUDASAACHA CORE
          </span>
        </div>
      </div>

      {/* Floating "live order" chips */}
      <div className="pointer-events-none absolute left-[6%] top-[14%] mp-float">
        <div className="flex items-center gap-2 rounded-md border border-buy/40 bg-buy/10 px-2.5 py-1 text-[10px] font-semibold text-buy backdrop-blur">
          <span className="size-1.5 rounded-full bg-buy" />
          BUY · NIFTY24FEB22800CE
          <span className="font-tabular">@ 184.50</span>
        </div>
      </div>
      <div className="pointer-events-none absolute right-[4%] top-[24%] mp-float mp-float-delay-1">
        <div className="flex items-center gap-2 rounded-md border border-sell/40 bg-sell/10 px-2.5 py-1 text-[10px] font-semibold text-sell backdrop-blur">
          <span className="size-1.5 rounded-full bg-sell" />
          SELL · BANKNIFTY FUT
          <span className="font-tabular">@ 48,612</span>
        </div>
      </div>
      <div className="pointer-events-none absolute bottom-[10%] left-[10%] mp-float mp-float-delay-2">
        <div className="flex items-center gap-2 rounded-md border border-primary/30 bg-background/70 px-2.5 py-1 text-[10px] font-semibold text-foreground backdrop-blur">
          <IndianRupee className="size-3 text-primary" />
          Margin used
          <span className="font-tabular text-primary">₹ 1,24,580</span>
        </div>
      </div>
      <div className="pointer-events-none absolute bottom-[16%] right-[8%] mp-float mp-float-delay-3">
        <div className="flex items-center gap-2 rounded-md border border-primary/30 bg-background/70 px-2.5 py-1 text-[10px] font-semibold text-foreground backdrop-blur">
          <span className="size-1.5 rounded-full bg-primary mp-spark" />
          Latency
          <span className="font-tabular text-primary">9 ms</span>
        </div>
      </div>

      {/* Up/down number sparks */}
      <div className="pointer-events-none absolute left-[42%] top-[2%]">
        <span className="font-tabular text-[11px] font-bold text-buy mp-tick-up">+12.40</span>
      </div>
      <div className="pointer-events-none absolute right-[12%] top-[6%]">
        <span className="font-tabular text-[11px] font-bold text-sell mp-tick-down mp-tick-delay-1">-3.20</span>
      </div>
      <div className="pointer-events-none absolute bottom-[2%] left-[28%]">
        <span className="font-tabular text-[11px] font-bold text-buy mp-tick-up mp-tick-delay-2">+45.80</span>
      </div>
      <div className="pointer-events-none absolute bottom-[6%] right-[24%]">
        <span className="font-tabular text-[11px] font-bold text-sell mp-tick-down mp-tick-delay-3">-1.15</span>
      </div>
    </div>
  );
}
