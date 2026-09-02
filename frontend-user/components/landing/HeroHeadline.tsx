"use client";

import { useEffect, useState } from "react";
import VaporizeTextCycle, { Tag } from "@/components/ui/vapour-text-effect";

/**
 * Hero headline: a static white line + a gold line that cycles through
 * brand phrases using the vaporize particle effect. ~3s per loop.
 */
export default function HeroHeadline() {
  const [fontSize, setFontSize] = useState("76px");

  useEffect(() => {
    const update = () => setFontSize(window.innerWidth < 768 ? "42px" : "76px");
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return (
    <div className="flex flex-col items-center">
      <h1 className="text-5xl md:text-7xl font-extrabold font-manrope leading-[1.02] tracking-tight max-w-5xl text-white">
        Where Smart Traders
      </h1>

      {/* Vaporizing gold line — cycles in a ~3s loop */}
      <div className="w-full max-w-5xl h-[56px] md:h-[104px] mt-1 overflow-hidden" aria-hidden="true">
        <VaporizeTextCycle
          texts={["Build Wealth", "Trade Smarter", "Grow Faster"]}
          color="rgb(230, 184, 57)"
          font={{ fontFamily: "Manrope, sans-serif", fontSize, fontWeight: 800 }}
          spread={5}
          density={5}
          animation={{ vaporizeDuration: 1.5, fadeInDuration: 1, waitDuration: 0.5 }}
          direction="left-to-right"
          alignment="center"
          tag={Tag.P}
        />
      </div>
    </div>
  );
}
