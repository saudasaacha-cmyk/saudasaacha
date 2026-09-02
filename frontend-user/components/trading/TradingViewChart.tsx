"use client";

import { useEffect, useRef, memo } from "react";
import { CustomDatafeed, pushLiveQuote } from "@/lib/tradingview-datafeed";

interface TradingViewChartProps {
  token: string;
  symbol?: string;
  interval?: string;
  theme?: "light" | "dark";
  className?: string;
  /** Live quote from the terminal's WebSocket stream. When provided, the
   *  chart's real-time bar uses this price instead of REST polling, so
   *  the chart and the order panel always show the same price. */
  quote?: { ltp?: number; bid?: number; ask?: number } | null;
}

function TradingViewChartInner({
  token,
  interval = "5",
  theme = "dark",
  className = "",
  quote,
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<any>(null);
  // Latest token always available to the build effect via ref — that way the
  // build effect only depends on `theme`, and a token change never tears the
  // widget down. (See the dedicated `[token]` effect below.)
  const tokenRef = useRef(token);
  tokenRef.current = token;

  // Push incoming WebSocket quote into the datafeed's live cache so the
  // chart's subscribeBars reads the same price as the order panel.
  useEffect(() => {
    if (!token || !quote) return;
    const ltp = Number(quote.ltp ?? 0);
    const bid = Number(quote.bid ?? 0);
    const ask = Number(quote.ask ?? 0);
    if (ltp > 0 || bid > 0) {
      pushLiveQuote(token, ltp, bid, ask);
    }
  }, [token, quote?.ltp, quote?.bid, quote?.ask]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Stable container id (no token suffix). When the user clicks a new
    // instrument we DON'T rebuild — we just call `activeChart().setSymbol()`
    // on the existing widget, so the id must stay the same across token
    // changes. Including the theme suffix is still safe because a theme
    // flip does rebuild the widget below.
    const containerId = `tv_chart_${theme}`;
    container.id = containerId;

    // Track cancellation so a fast re-render (React strict-mode double-mount,
    // theme flip) doesn't end up initialising a widget on a container that's
    // already been torn down.
    let cancelled = false;

    const loadWidget = () => {
      if (cancelled) return;
      if (!window.TradingView) {
        // Tight 25 ms poll while we wait for the script. With the layout
        // preload most cold loads land on the first iteration; we just
        // need a cheap fallback for the racy script-loaded-but-not-yet-
        // assigned-window window.
        setTimeout(loadWidget, 25);
        return;
      }
      // Verify the container is still in the DOM at the moment we hand it
      // to the widget. Without this check React's effect cleanup can have
      // already removed it, and the widget throws "no such element".
      if (!document.getElementById(containerId)) return;

      if (widgetRef.current) {
        try {
          widgetRef.current.remove();
        } catch {}
        widgetRef.current = null;
      }

      const datafeed = new CustomDatafeed();

      try {
        widgetRef.current = new window.TradingView.widget({
          // Pass the live element reference, not just the id string — even if
          // React swaps containers under us this still resolves correctly.
          container,
          datafeed,
          // Use the ref so a token change that lands between mount and the
          // moment the script finishes loading still picks the latest value.
          symbol: tokenRef.current,
          interval,
          library_path: "/charting_library/",
          locale: "en",
          fullscreen: false,
          autosize: true,
          theme: theme === "dark" ? "dark" : "light",
          timezone: "Asia/Kolkata",
          disabled_features: [
            "use_localstorage_for_settings",
            "header_symbol_search",
            "header_compare",
            "display_market_status",
            "go_to_date",
            "study_templates",
            "chart_storage",
            // Skip the default volume indicator creation — it adds another
            // study (extra getBars + render pass) on every chart init. Users
            // who want volume can add it from the Indicators dialog.
            "create_volume_indicator_by_default",
            // Avoid forcing the volume pane overlay; one less layout calc.
            "volume_force_overlay",
            // Drawing-tools rail hidden on phones — it overlaps the candles
            // on a narrow viewport (operator: "side vale tools mat dikh").
            // Full charting library needs this in disabled_features (the
            // `hide_side_toolbar` widget option is ignored here). Desktop
            // keeps the toolbar.
            ...(typeof window !== "undefined" &&
            window.matchMedia("(max-width: 1023px)").matches
              ? ["left_toolbar"]
              : []),
          ],
          enabled_features: [
            // Pulls the last-bar price label out as a tracked horizontal
            // line on the right-side scale — without this the user can't
            // see where the live price sits relative to the visible range.
            "move_logo_to_main_pane",
            // Show the timeframes toolbar (1D / 5D / 1M / 3M / 6M / YTD / 1Y)
            // along the bottom of the chart on desktop — matches what users
            // see on TradingView.com and Zerodha Kite, gives one-tap access
            // to the common range presets without going through the
            // timeframe dropdown.
            "timeframes_toolbar",
            // Show the symbol + last price legend at the top-left of the
            // chart pane. Already on by default but explicit so a future
            // disabled_features add doesn't accidentally turn it off.
            "header_widget",
            // Bottom-of-pane date scale gets the range selector buttons
            // (1D / 1W / 1M …) — same as TradingView's public chart UI.
            "header_resolutions",
          ],
          overrides: {
            "paneProperties.background": theme === "dark" ? "#131122" : "#ffffff",
            "paneProperties.backgroundType": "solid",
            "paneProperties.vertGridProperties.color": theme === "dark" ? "#1e1c30" : "#e9e9ea",
            "paneProperties.horzGridProperties.color": theme === "dark" ? "#1e1c30" : "#e9e9ea",
            "scalesProperties.backgroundColor": theme === "dark" ? "#131122" : "#ffffff",
            "scalesProperties.textColor": theme === "dark" ? "#8a86a8" : "#555",
            "scalesProperties.lineColor": theme === "dark" ? "#1e1c30" : "#e0e0e0",
            "mainSeriesProperties.candleStyle.upColor": "#2bca6a",
            "mainSeriesProperties.candleStyle.downColor": "#ec5d6f",
            "mainSeriesProperties.candleStyle.wickUpColor": "#2bca6a",
            "mainSeriesProperties.candleStyle.wickDownColor": "#ec5d6f",
            "mainSeriesProperties.candleStyle.borderUpColor": "#2bca6a",
            "mainSeriesProperties.candleStyle.borderDownColor": "#ec5d6f",
            // Horizontal price line at the last close — the key signal the
            // user lost without it ("price move dikh nahi raha"). Dashed
            // purple to match the app's accent colour so it stands apart
            // from the candle wicks.
            "mainSeriesProperties.priceLineVisible": true,
            "mainSeriesProperties.priceLineColor": "#8e7df0",
            "mainSeriesProperties.priceLineWidth": 1,
            "mainSeriesProperties.showCountdown": true,
            // High-watermark crosshair so price reads are obvious as the
            // user hovers across candles.
            "paneProperties.crossHairProperties.color": theme === "dark" ? "#8a86a8" : "#555",
            "paneProperties.crossHairProperties.style": 2,
          },
          loading_screen: {
            backgroundColor: theme === "dark" ? "#131122" : "#ffffff",
            foregroundColor: theme === "dark" ? "#8e7df0" : "#3b82f6",
          },
          custom_css_url: "",
        });

        // Once the chart is initialised, tighten the right-offset so the
        // candle stream fills the pane (default is ~10 bars of future
        // whitespace which is what was making the chart look squashed
        // to the right edge), and force a layout pass against the live
        // container size — autosize alone doesn't catch a parent that
        // grows AFTER the widget mounted.
        try {
          widgetRef.current.onChartReady?.(() => {
            try {
              widgetRef.current.activeChart().setRightOffset(5);
            } catch {}
            // Force-fit the widget to the current container bounds the
            // moment the chart is ready. `autosize: true` watches the
            // iframe's own size, not the parent flex container — on
            // first mount the parent often grows from 0 → final size
            // AFTER the widget initialises, leaving the iframe stuck
            // at its initial (tiny) dimensions. Explicit resize here
            // kicks it into the actual layout. This is the fix for
            // "chart bahut chhota dikh raha hai" on mobile.
            try {
              const rect = container.getBoundingClientRect();
              if (rect.width > 0 && rect.height > 0) {
                widgetRef.current.resize?.(rect.width, rect.height);
              }
            } catch {}
          });
        } catch {}
      } catch (err) {
        console.error("TradingView widget init error:", err);
      }
    };

    // Load the TradingView standalone script if not already loaded.
    // The terminal route layout preloads this via `next/script` so on most
    // navigations the script is already in flight (or fully loaded) by the
    // time we get here — we still keep the manual injection as a fallback
    // for direct entry / cold cache.
    // Match both src patterns Next.js can produce: the raw `/charting_…`
    // tag we inject ourselves, and any tag carrying that path (Next's
    // <Script> emits an absolute URL on some builds).
    const alreadyInjected = !!document.querySelector(
      'script[src*="charting_library.standalone.js"]',
    );
    if (window.TradingView) {
      // Script fully loaded already (via the layout preload) — skip the
      // polling round-trip entirely and init the widget on the same tick.
      loadWidget();
    } else if (alreadyInjected) {
      // Script tag exists but is still downloading — start the poll loop;
      // first iteration will catch it the moment `window.TradingView` is
      // assigned.
      loadWidget();
    } else {
      const script = document.createElement("script");
      script.src = "/charting_library/charting_library.standalone.js";
      script.async = true;
      script.onload = loadWidget;
      document.head.appendChild(script);
    }

    // TV's autosize watches the iframe size, but when the *parent flex
    // container* resizes (laptop → external monitor, panel toggle, window
    // drag across screens) the embedded iframe sometimes keeps the stale
    // dimensions until the next mouse interaction. ResizeObserver forces
    // a relayout in lockstep with the container — the actual fix for the
    // "chart har screen pe alag dikh raha hai" complaint.
    const ro = new ResizeObserver(() => {
      const w = widgetRef.current;
      if (!w) return;
      try {
        // resize(width, height) re-fits the chart to the new bounds; both
        // dimensions are read live so it works on any screen size.
        const rect = container.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          w.resize?.(rect.width, rect.height);
        }
      } catch {}
    });
    ro.observe(container);

    return () => {
      cancelled = true;
      ro.disconnect();
      if (widgetRef.current) {
        try {
          widgetRef.current.remove();
        } catch {}
        widgetRef.current = null;
      }
    };
    // Intentionally [theme] only: changing the token swaps the symbol on the
    // live widget (effect below) instead of tearing it down and rebuilding.
    // Recreating cost ~500 ms-1 s per click (script poll + resolveSymbol +
    // getBars + TV init) — the dominant complaint about "chart slow load".
    // Interval changes are handled by their own effect further down.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  // ── Token change: in-place symbol swap ────────────────────────────
  // When the user clicks a new instrument we keep the existing widget and
  // ask TradingView to load the new symbol — skipping the loading screen,
  // widget init, datafeed reconstruction, and ResizeObserver re-wire. Only
  // resolveSymbol + getBars happen, which is the irreducible minimum work
  // any chart needs on a token change.
  useEffect(() => {
    const w = widgetRef.current;
    if (!w || !token) return;
    try {
      w.onChartReady(() => {
        try {
          w.activeChart().setSymbol(token);
        } catch (e) {
          // setSymbol can throw if the widget was torn down mid-flight.
          console.error("TradingView setSymbol failed:", e);
        }
      });
    } catch {}
  }, [token]);

  // Handle interval changes
  useEffect(() => {
    if (widgetRef.current) {
      try {
        widgetRef.current.onChartReady(() => {
          widgetRef.current.activeChart().setResolution(interval);
        });
      } catch {}
    }
  }, [interval]);

  return (
    <div
      ref={containerRef}
      // `absolute inset-0` forces the container to fill its (relative)
      // parent regardless of flex / intrinsic-size quirks — that's the
      // robust fix for the "chart faat raha" symptom where TradingView's
      // iframe got stuck at its initial small bounds because the parent
      // chart wrapper was reporting 0 × 0 at widget-init time. The
      // parent in `terminal/page.tsx` is `relative` + has a definite
      // `h-[calc(100vh-13rem)]` on mobile, so this absolute child gets
      // the same definite size and TV's autosize has a real bounding
      // box to fit into. Inline style + Tailwind class both included so
      // the rule still applies if a stray utility class disables `inset`.
      style={{ position: "absolute", inset: 0 }}
      className={`block ${className}`}
    />
  );
}

// Add TradingView type declaration
declare global {
  interface Window {
    TradingView: any;
  }
}

export const TradingViewChart = memo(TradingViewChartInner);
