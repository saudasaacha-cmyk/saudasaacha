"use client";

import { useEffect, useRef, useState, memo } from "react";
import { CustomDatafeed, pushLiveQuote } from "@/lib/tradingview-datafeed";
import { InstrumentAPI, type ChartLevel } from "@/lib/api";

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
  // Flips once the widget exists AND its chart is ready. The widget is
  // built asynchronously (script load → widget init → onChartReady), so an
  // effect that merely reads `widgetRef.current` runs BEFORE it exists and,
  // having no reason to re-run, never draws anything. Anything that has to
  // talk to the chart depends on this instead.
  const [chartReady, setChartReady] = useState(0);
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
            // Bumped (not set true) so a widget REBUILD — theme switch tears
            // the widget down and makes a new one — re-runs the dependants
            // even though the previous value was already "ready".
            setChartReady((n) => n + 1);
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

  // ── Admin-defined price lines ─────────────────────────────────────
  // Re-asked for this often: the admin edits a level on another screen and
  // the trader's open chart has to follow. 20 s is invisible to a person and
  // the payload is a handful of numbers.
  const LEVEL_POLL_MS = 20_000;

  // The admin uploads price + colour per instrument from the admin panel;
  // each one is drawn here as a horizontal line in that colour. Redrawn on
  // every token change, and the previous instrument's lines are removed
  // first — TradingView keeps shapes on the chart across a setSymbol(), so
  // without this the last symbol's levels stay floating over the new one.
  const levelShapesRef = useRef<any[]>([]);
  // Uptrend / Downtrend / Sideways, as the admin marked it in the levels
  // sheet. Drawn as a chip over the chart rather than as a shape — a shape
  // would sit at a price, and a trend doesn't have one.
  const [trend, setTrend] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    let dataSub: any = null;
    let timer: number | null = null;

    const clear = () => {
      const w = widgetRef.current;
      const ids = levelShapesRef.current;
      levelShapesRef.current = [];
      if (!w) return;
      for (const id of ids) {
        try {
          w.activeChart().removeEntity(id);
        } catch {
          // Entity already gone (symbol switch, widget rebuild) — nothing to do.
        }
      }
    };

    // What the server last told us to draw. Kept in a ref so a repaint
    // (bars reloaded, symbol switched back) doesn't need another round trip.
    const levelsRef: { current: ChartLevel[] } = { current: [] };
    let lastJson = "";

    const paint = async () => {
      if (cancelled) return;
      const w = widgetRef.current;
      if (!w) return;
      const chart = w.activeChart();
      clear();
      // A horizontal line still needs a time coordinate. The visible range
      // can be empty on the first ready tick, so fall back to "now" — the
      // time is irrelevant once the line spans the pane.
      let anchor = Math.floor(Date.now() / 1000);
      try {
        const vr = chart.getVisibleRange?.();
        if (vr && Number.isFinite(vr.from) && vr.from > 0) anchor = vr.from;
      } catch {}
      for (const lv of levelsRef.current) {
        if (!Number.isFinite(lv.price) || lv.price <= 0) continue;
        try {
          // createShape resolves to the id — it does NOT return it. Reading
          // the promise as an id meant every failure below surfaced as an
          // unhandled rejection: nothing drawn, nothing logged, and the
          // "ids" we kept for cleanup were promises.
          const id = await chart.createShape(
            { time: anchor, price: lv.price },
            {
              shape: "horizontal_line",
              lock: true, // an admin level is not the user's to drag
              disableSelection: true,
              disableSave: true,
              disableUndo: true,
              zOrder: "top",
              text: lv.label || "",
              // Per-shape overrides are the TOOL's own property names —
              // `linecolor`, not `linetoolhorzline.linecolor`. The prefixed
              // form belongs to widget.applyOverrides() (global defaults).
              //
              // Getting this wrong is SILENT: the library walks the keys
              // with `properties.hasChild(key)` and just skips anything it
              // doesn't recognise. No throw, no warning — every line simply
              // kept the tool's factory default #2962FF, which is why they
              // all came out the same blue however many colours the admin
              // set. Hence the read-back check below.
              overrides: {
                linecolor: lv.color,
                linewidth: 2,
                linestyle: 0,
                showPrice: true,
                textcolor: lv.color,
                horzLabelsAlign: "right",
                vertLabelsAlign: "bottom",
              },
            },
          );
          if (cancelled) break;
          if (id) {
            levelShapesRef.current.push(id);
            // The override API can't report a key it ignored, so confirm the
            // colour actually landed. One line in the console beats every
            // line on the chart being the same colour and nobody knowing why.
            try {
              const applied = chart.getShapeById(id)?.getProperties?.()?.linecolor;
              if (applied && String(applied).toLowerCase() !== lv.color.toLowerCase()) {
                console.warn(
                  "chart level colour was ignored by the library",
                  { wanted: lv.color, applied, label: lv.label },
                );
              }
            } catch {}
          }
        } catch (e) {
          console.error("chart level draw failed", lv, e);
        }
      }
    };

    // Ask the server what to draw. Repaints only when the answer CHANGED,
    // so the poll below costs one small request and nothing else.
    const refresh = async () => {
      const w = widgetRef.current;
      if (!w || !token || cancelled) return;
      let levels: ChartLevel[] = [];
      let t: string | null = null;
      try {
        // The endpoint returned a bare array before the trend was added; a
        // browser running yesterday's bundle against today's API (or the
        // reverse) must still draw its lines.
        const res = await InstrumentAPI.chartLevels(token);
        if (Array.isArray(res)) {
          levels = res;
        } else {
          levels = res?.levels ?? [];
          t = res?.trend ?? null;
        }
      } catch {
        return; // call failed — leave what is on the chart alone
      }
      if (cancelled) return;
      setTrend(t);
      const json = JSON.stringify(levels);
      if (json === lastJson) return;
      lastJson = json;
      levelsRef.current = levels;
      // Also the path that CLEARS: an admin who deleted every line sends an
      // empty list, and paint() removes the shapes without drawing new ones.
      void paint();
    };

    // Coming back to the tab should show the current lines straight away,
    // not up to one poll later.
    const onVisible = () => {
      if (!document.hidden) void refresh();
    };

    setTrend(null); // the last symbol's trend must not linger on this one
    if (chartReady > 0) {
      const w = widgetRef.current;
      try {
        w?.onChartReady(() => {
          if (cancelled) return;
          try {
            // Bars land AFTER onChartReady and reload on every symbol switch;
            // repaint so the levels survive both. Subscribed ONCE — the poll
            // below must not stack a new subscription every time it runs.
            dataSub = w.activeChart().onDataLoaded();
            dataSub.subscribe(null, () => void paint());
          } catch {}
          void refresh();
        });
      } catch {}
      // These lines are edited on another screen, by someone else. Without a
      // poll a trader keeps whatever was set the moment they opened the
      // chart — the admin edits a level, saves, and nothing moves here.
      timer = window.setInterval(() => {
        if (!document.hidden) void refresh();
      }, LEVEL_POLL_MS);
      document.addEventListener("visibilitychange", onVisible);
    }
    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      try {
        dataSub?.unsubscribeAll?.(null);
      } catch {}
      clear();
    };
  }, [token, chartReady]);

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

  const chart = (
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

  // The container belongs to TradingView — it replaces its contents — so the
  // chip is a SIBLING positioned over it, not a child.
  return trend ? (
    <>
      {chart}
      <div
        className={`pointer-events-none absolute bottom-10 left-2 z-10 rounded px-2 py-0.5 text-[11px] font-semibold tracking-wide ${TREND_STYLE[trend] ?? "bg-white/10 text-white/70"}`}
      >
        {trend.toUpperCase()}
      </div>
    </>
  ) : (
    chart
  );
}

// Buy-green / sell-red are the locked theme colours; sideways is deliberately
// neutral so it doesn't read as a signal.
const TREND_STYLE: Record<string, string> = {
  Uptrend: "bg-[#10b981]/15 text-[#10b981]",
  Downtrend: "bg-[#ef4444]/15 text-[#ef4444]",
  Sideways: "bg-white/10 text-white/70",
};

// Add TradingView type declaration
declare global {
  interface Window {
    TradingView: any;
  }
}

export const TradingViewChart = memo(TradingViewChartInner);
