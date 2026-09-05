// Map a SachchaSauda instrument to a FREE TradingView public symbol
// (OANDA / BINANCE / TVC) so the international (Infoway-fed) instruments —
// forex, spot metals, energy, crypto — can render in the free tv.js Advanced
// Chart widget with TradingView's own real data + full features.
//
// Returns `null` for Indian instruments (NSE / BSE / NFO / BFO / MCX) and for
// anything we can't confidently map — those keep the LICENSED chart that runs
// off our own datafeed (exact broker price). Operator decision: free widget
// for international, licensed for Indian.
//
// Caveat (accepted): the free widget shows TradingView's liquidity (OANDA /
// Binance), which is very close to but NOT identical to our Infoway price. The
// BUY/SELL order bar still uses our price.

const INDIAN_EXCH = new Set(["NSE", "BSE", "NFO", "BFO", "MCX"]);

// Crypto bases we serve → Binance USDT pair.
const CRYPTO_BASES = new Set([
  "BTC", "ETH", "LTC", "XRP", "SOL", "BNB", "DOGE", "ADA", "TRX", "LINK",
  "DOT", "AVAX", "MATIC", "ATOM", "NEAR", "ARB", "OP", "APT", "SUI", "PEPE",
  "SHIB", "BCH", "FIL", "TON", "INJ",
]);

// Energy → OANDA CFD names (reliable free TradingView symbols).
const ENERGY: Record<string, string> = {
  USOIL: "OANDA:WTICOUSD",
  WTI: "OANDA:WTICOUSD",
  UKOIL: "OANDA:BCOUSD",
  BRENT: "OANDA:BCOUSD",
  NATGAS: "OANDA:NATGASUSD",
};

export function toPublicTvSymbol(
  symbol?: string | null,
  exchange?: string | null,
  segment?: string | null,
): string | null {
  const s = (symbol ?? "").toUpperCase().replace(/\s+/g, "");
  const ex = (exchange ?? "").toUpperCase();
  const seg = (segment ?? "").toUpperCase();
  if (!s) return null;

  // Indian exchanges → keep the licensed chart (our exact datafeed).
  if (INDIAN_EXCH.has(ex)) return null;

  // Crypto and forex → licensed chart too. Both now have real history on our
  // own backend (Binance klines for crypto, Yahoo for FX) and crypto has a
  // live Binance tick, so the licensed chart shows OUR price with the full
  // drawing/indicator toolset instead of TradingView's own liquidity. Metals
  // and energy stay on the free widget below until they have a live feed.
  if (ex === "CRYPTO" || seg.includes("CRYPTO") || seg.includes("FOREX")) return null;

  // ── Crypto → Binance pair ──────────────────────────────────────────
  if (s.endsWith("USDT") || s.endsWith("USDC")) return `BINANCE:${s}`;
  const base = s.endsWith("USD") ? s.slice(0, -3) : "";
  if (base && CRYPTO_BASES.has(base)) return `BINANCE:${base}USDT`;
  if (ex === "CRYPTO" || seg.includes("CRYPTO")) {
    return `BINANCE:${s.replace(/USD$/, "USDT")}`;
  }

  // ── Energy CFDs ────────────────────────────────────────────────────
  if (ENERGY[s]) return ENERGY[s];

  // ── Forex + spot metals (EURUSD, XAUUSD, XAGUSD, …) → OANDA CFD ─────
  // OANDA covers all the 6-letter FX crosses plus the metals we list, which
  // is exactly the international set the free widget should serve.
  if (/^[A-Z]{6}$/.test(s)) return `OANDA:${s}`;

  // International but unmappable → licensed chart handles it.
  return null;
}
