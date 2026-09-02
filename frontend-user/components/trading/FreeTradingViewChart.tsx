"use client";

import { memo, useEffect, useRef } from "react";

// FREE TradingView "Advanced Chart" — used ONLY for international instruments
// (forex / metals / energy / crypto) via a mapped public symbol
// (OANDA:XAUUSD, OANDA:EURUSD, BINANCE:BTCUSDT, …). TradingView supplies the
// data + full toolbar for free. Indian instruments keep the licensed
// <TradingViewChart> (our datafeed, exact broker price).
//
// IMPORTANT: we use the EMBED widget (embed-widget-advanced-chart.js), NOT the
// `tv.js` widget. The licensed Charting Library and `tv.js` BOTH define
// `window.TradingView` with incompatible config schemas — loading both made
// the free chart render blank. The embed widget runs in its own isolated
// iframe, so it coexists cleanly with the licensed library on the same page.

interface Props {
  /** Already-mapped TradingView public symbol, e.g. "OANDA:XAUUSD". */
  tvSymbol: string;
  /** Initial interval ("1" / "5" / "15" / "60" / "1D"). */
  interval: string;
  theme?: "light" | "dark";
  className?: string;
}

const EMBED_SCRIPT =
  "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";

function FreeTradingViewChartInner({ tvSymbol, interval, theme = "dark", className = "" }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Latest interval available to the (symbol/theme-keyed) build effect
  // without making interval a dependency — a timeframe-bar click shouldn't
  // tear down and reload the iframe.
  const intervalRef = useRef(interval);
  intervalRef.current = interval;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Rebuild from scratch for the new symbol/theme.
    container.innerHTML = "";

    const widget = document.createElement("div");
    widget.className = "tradingview-widget-container__widget";
    widget.style.height = "100%";
    widget.style.width = "100%";
    container.appendChild(widget);

    const script = document.createElement("script");
    script.src = EMBED_SCRIPT;
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tvSymbol,
      interval: intervalRef.current || "5",
      timezone: "Asia/Kolkata",
      theme: theme === "dark" ? "dark" : "light",
      style: "1", // candles
      locale: "en",
      hide_side_toolbar: false,
      allow_symbol_change: false,
      withdateranges: true,
      details: false,
      calendar: false,
      support_host: "https://www.tradingview.com",
    });
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
    // interval intentionally excluded — see intervalRef note above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tvSymbol, theme]);

  return (
    <div
      ref={containerRef}
      className={`tradingview-widget-container block ${className}`}
      style={{ position: "absolute", inset: 0, height: "100%", width: "100%" }}
    />
  );
}

export const FreeTradingViewChart = memo(FreeTradingViewChartInner);
