# Where every price comes from — and how to wire the same feeds into another project

Measured on production, 2026-10-08. Three live feeds, no others; MetaAPI and
Infoway are gone.

This file is two things: a map of what SachchaSauda runs today, and enough
detail to rebuild the same data layer somewhere else. The last section is a
prompt you can hand to Claude in another repo.

---

## 1. The short version

| Feed | Serves | Cost | Auth |
|---|---|---|---|
| **Binance USDT-M futures** | Crypto, metals, energy, world index ETFs, US + Asian stocks — 743 instruments | Free | None |
| **Binance spot** | Eight legacy `CRYPTO_*` rows | Free | None |
| **Zerodha Kite** | Every Indian segment (NSE, NFO, BFO, MCX) | Paid subscription | API key + daily access token |
| **Yahoo Finance chart API** | Historical candles for everything Binance klines don't cover | Free, throttled | None (needs a real User-Agent) |

**Gold and silver do not come from COMEX.** `XAUUSD` is Binance's `XAUUSDT`
perpetual. So are the rest of the metals, both oils, the index ETFs and all
193 stocks. Candles for them come from Yahoo's COMEX/NYMEX front month,
shifted onto the live Binance price. Details in §4 and §6.

---

## 2. What is live right now, by segment

| Segment | Active | Source | Examples |
|---|---:|---|---|
| CRYPTO_SPOT | 528 | binance_futures (520) + binance spot (8) | BTCUSD, ETHUSD, 1000000MOG |
| STOCKS | 193 | **binance_futures** | AAPL, NVDA, MSTR, MU, SOXL |
| NFO_OPTION | 336 | zerodha | NIFTY / BANKNIFTY / stock CE+PE |
| BFO_OPTION | 226 | zerodha | SENSEX CE+PE |
| MCX_OPTION | 222 | zerodha | CRUDEOIL 8100 CE/PE |
| NSE_EQUITY | 147 | zerodha | RELIANCE, HDFCBANK |
| MCX_FUTURE | 111 | zerodha | GOLD26DECFUT, SILVER26DECFUT |
| NFO_FUTURE | 49 | zerodha | NIFTY26OCTFUT |
| INDICES | 14 | **binance_futures** | SPY, QQQ, IWM, GDX, EWJ |
| COMMODITIES | 8 | **binance_futures** | XAUUSD, XAGUSD, USOIL, NATGAS |
| BSE_EQUITY / BFO_FUTURE | 5 | zerodha | thin, often no live tick |

"Active" is the catalogue count, not how many are ticking at any instant: an
Indian contract only ticks while its exchange is open, and an illiquid
far-month one trades a few times an hour.

Every live quote is mirrored to Redis as `mdlive:{token}` carrying the
`source` field this table was counted from, so it can be re-measured instead
of believed:

```bash
redis-cli --raw get mdlive:XAUUSD | python -m json.tool   # "source": "binance_futures"
```

---

## 3. Binance USDT-M futures — the one that does the heavy lifting

`backend/app/services/binance_futures_service.py`

```
WS   wss://fstream.binance.com/ws
REST https://fapi.binance.com
```

No API key. No per-symbol entitlement. One connection covers the whole
exchange, which is the property that makes it worth building on: adding the
700th instrument costs nothing.

### Three streams, because the all-market one is sampled

| Stream | What it gives | Measured rate |
|---|---|---|
| `!bookTicker` | best bid/ask for **every** contract | 0.20 updates/s per symbol — coverage, not speed |
| `<symbol>@bookTicker` | the same book for one contract | 64.8 updates/s — 324× faster |
| `<symbol>@aggTrade` | the **last traded** price | this is what makes a chart look alive |
| REST `/fapi/v1/ticker/24hr` | open / high / low / change, all symbols | polled every 10 s |

Why both book and trades: `XAUUSDT`'s book sends ~84 messages a second but its
bid/ask only *moves* twice a second — most messages are size changes at the
same price. Binance's own screen looks alive because it prints trades. So:
**trade price = last price, book = bid/ask**, and a trade owns the last price
for 3 s before the mid takes over again.

`!ticker@arr` would have carried the 24 h stats over the socket, but on this
endpoint it is acknowledged and then never delivers a frame — hence the REST
poll.

### The fast lane, and its ceiling

Binance allows **1024 streams per connection** and **200 params per SUBSCRIBE**.
Two streams per symbol, so the hot set is capped at **300 contracts** (600
streams) with room left for the all-market stream. A symbol enters the hot set
when someone looks at it and ages out after **15 minutes** unasked; the lane is
reconciled every 5 s, subscribing in chunks of 150.

Other constants worth copying:

| Constant | Value | Why |
|---|---|---|
| `_STALE_RX_TIMEOUT_SEC` | 30 | a silent socket is a half-open socket — force a reconnect |
| `_RECONNECT_CAP_SEC` | 60 | exponential backoff ceiling |
| `_STABLE_CONNECTION_SEC` | 30 | connection must survive this long before backoff resets |
| `_MAX_TICK_SPIKE_PCT` | 0.5 | one lone print this far off is garbage, not a move — drop it |

### Symbol resolution — one function, used twice

```python
def contract_for(sym, known):      # known = set of Binance contract names
    if sym in known: return sym                 # AAPLUSDT  → itself
    if _ALIASES.get(sym) in known: return ...   # USOIL     → CLUSDT
    for cand in (sym + "T", sym + "USDT"):      # BTCUSD    → BTCUSDT
        if cand in known: return cand           # AAPL      → AAPLUSDT
    return None
```

The renames that cannot be derived:

| Platform symbol | Binance contract | |
|---|---|---|
| XAUUSD | XAUUSDT | gold |
| XAGUSD | XAGUSDT | silver |
| XPTUSD | XPTUSDT | platinum |
| XPDUSD | XPDUSDT | palladium |
| USOIL | **CLUSDT** | WTI |
| UKOIL | **BZUSDT** | Brent |
| NATGAS | NATGASUSDT | |
| COPPER | COPPERUSDT | |

The feed and the catalogue sync share this one function on purpose: two copies
of the rule is how you end up seeding a duplicate instrument for a symbol that
was already covered.

### Letting Binance classify the catalogue

`backend/app/services/binance_catalogue_service.py` mirrors
`GET /fapi/v1/exchangeInfo` (~790 contracts) into the instrument collection and
takes the segment from Binance's own `underlyingType`:

```
COMMODITY                                   → COMMODITIES
EQUITY / HK_ / KR_ / CN_EQUITY / PREMARKET  → STOCKS
COIN, plus the crypto indices (BTCDOM, ALL) → CRYPTO_SPOT
FX                                          → skipped
```

Three rules keep it safe to re-run:

* Only **USDT**-quoted contracts. The USDC / USD1 duplicates quote the same
  asset and would put two rows for one instrument in front of the user.
* Instruments already in the catalogue are **left alone** — `XAUUSD` keeps its
  token, its open positions and its trade history, and merely gets its price
  from `XAUUSDT`.
* It only ever touches `COMMODITIES / STOCKS / INDICES / CRYPTO_SPOT`. Zerodha's
  NSE and MCX rows are none of its business.

Two hand-kept lists: `_INDEX_ETFS` (Binance files QQQ and SPY as equities;
users look for them under Indices) and `_NICE_NAMES` (the listing carries
tickers only, so a browse would read "CAT, CBRS, CIEN, COHR" with nothing to
tell them apart).

### The caveat that matters commercially

**These are perpetual futures.** Funding settles every 8 h and the contract
carries a basis to spot — measured ~0.05% on gold. Close to COMEX, never
identical. A client comparing against a COMEX screen will see a few dollars of
difference; that is the instrument, not a bug. (The PAXG *token* on Binance
spot runs ~0.27% off spot, which is why an earlier survey of the spot market
concluded "only gold is available" and was wrong.)

---

## 4. Binance spot

`backend/app/services/binance_service.py` — `wss://stream.binance.com:9443/stream`,
combined streams, three per symbol (`@aggTrade`, `@bookTicker`, `@ticker`).
Symbol list comes from `BINANCE_CRYPTO_SYMBOLS` in the env. It survives only
because eight legacy `CRYPTO_*` instrument rows predate the futures feed. A new
project should start with the futures feed and skip this entirely.

---

## 5. Zerodha Kite (Indian segments)

Needs a paid Kite Connect subscription, an API key/secret and a daily access
token (auto-login is scripted in `zerodha_auto_login.py`). Instruments are keyed
by Kite's **numeric instrument token** — not the symbol — and that distinction
caused real outages here: a row whose `symbol` was `"341249"` is a row that can
never be found in search or re-subscribed by name.

Mechanics: WS subscribe in FULL mode per token (on demand, capped), REST
`instruments(exchange)` for the catalogue (cache it — the CSV is ~1 MB and slow),
REST `quote()` as the cold-start fallback when the WS has not ticked yet.

Nothing in this layer is reusable without a Kite subscription. Everything in §3
is reusable by anyone.

---

## 6. Candles come from somewhere else than the tick

A chart shows two things from two sources, and forgetting this is how a chart
ends up at the right shape on the wrong scale.

| Instrument | Live tick | History |
|---|---|---|
| Crypto | Binance | Binance klines |
| Metals / energy | Binance perp | Yahoo **COMEX/NYMEX front month** |
| Indices / US stocks | Binance perp | Yahoo index / plain ticker |
| Indian | Zerodha WS | Kite historical API |

### Binance klines

```
GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=1000
```

Free, no key, rate-limited per IP. `limit` is hard-capped at 1000, so the window
is computed from candles-per-day × days. Response rows are
`[openTime_ms, open, high, low, close, volume, …]`.

### Yahoo chart API

```
GET https://query1.finance.yahoo.com/v8/finance/chart/GC=F
    ?interval=5m&range=5d&includePrePost=false
```

* **A real `User-Agent` is required** — Yahoo blocks httpx's default.
* Intervals: `1m 3m 5m 15m 30m 60m 1d`. Lookback caps are strict: 1m → 7 days,
  5m → 60 days, 15m/30m/60m → 730 days.
* Response: `chart.result[0].timestamp[]` + `indicators.quote[0].{open,high,low,close,volume}[]`,
  with nulls for untraded slots that must be skipped.

The symbol map that matters:

| Ours | Yahoo | |
|---|---|---|
| XAUUSD | `GC=F` | COMEX gold front month |
| XAGUSD | `SI=F` | COMEX silver |
| XPTUSD / XPDUSD | `PL=F` / `PA=F` | |
| USOIL / UKOIL | `CL=F` / `BZ=F` | WTI / Brent |
| NATGAS | `NG=F` | |
| US30 / NAS100 / SPX500 | `^DJI` / `^NDX` / `^GSPC` | |
| UK100 / DE40 / JPN225 / HK50 | `^FTSE` / `^GDAXI` / `^N225` / `^HSI` | |
| US stocks | plain ticker (`AAPL`) | |
| FX pairs | `EURUSD=X` | 6 alpha chars + `=X` |

**`XAUUSD=X` resolves but serves ZERO intraday candles** (measured: 0 bars,
against `EURUSD=X`'s 1295). That single fact is why metals need the futures
symbol. Pin it in a test.

### Aligning the two

Yahoo's contract trades a little away from the live feed, so the series is
shifted before it reaches the chart:

```python
off = live_ltp - candles[-1]["close"]
if abs(off) / candles[-1]["close"] >= 0.0015:      # same-scale feeds are left alone
    for c in candles:
        for k in ("open", "high", "low", "close"):
            c[k] += off
```

Result: the real intraday shape, on the price the BUY/SELL buttons use. Without
it the chart and the order panel disagree by ~40 points on gold, and the live
tick injected into the last bar flickers between the two scales.

History is cached 60 s in-process per `(token, interval, days)`.

---

## 7. How the pieces fit in one process

Worth copying wholesale; each line is a bug that was fixed once.

* **One leader runs the feeds.** Workers elect a leader through Redis
  (`leader:feed`); only that one holds the sockets. Everything else would mean
  four connections and four sets of ticks.
* **`mdlive:{token}`, 30 s TTL**, written by the leader every tick. Non-leader
  workers read it instead of hitting the upstream. Short TTL on purpose: a dead
  leader must not keep feeding prices that look live. **Consequence to plan for:**
  an instrument that trades less often than every 30 s reads as "no price" on a
  non-leader worker, so blotters need a last-known fallback (`mdlast:{token}`,
  display only, never for a fill).
* **Pub/sub fanout** on `market:tick:{token}` so every worker's WebSocket clients
  see the same tick.
* **A 100 ms pump** (`MARKET_TICK_SEC`) drives the push to browsers. Measured:
  Binance moves in bursts, and 100 ms already carries every real move — 359 raw
  changes in 30 s collapsed to 39 distinct 100 ms windows. Going lower buys
  nothing but CPU.
* **Price for display ≠ price for execution.** Keep two accessors: a strict one
  that returns 0 when there is no live price (every order path depends on that),
  and a display one that falls back to the last known price. Mixing them either
  fills at a stale price or blanks a blotter's P&L to zero.

---

## 8. Prompt for building this in another project

Copy everything between the lines into the other repo's Claude, together with
this file.

---

> I want the same market-data layer this document describes, in **this** project.
> Read `price-feeds.md` first; it is measured from a running system, so prefer it
> over your own assumptions about what Binance offers.
>
> **Build, in this order:**
>
> 1. **Catalogue sync.** `GET https://fapi.binance.com/fapi/v1/exchangeInfo`,
>    keep USDT-quoted contracts only, and classify by Binance's own
>    `underlyingType` into commodities / stocks / crypto exactly as §3 describes.
>    Make it idempotent: re-running must never duplicate or renumber an existing
>    instrument.
> 2. **One `contract_for(symbol, known)`** implementing exact → alias → `+T` →
>    `+USDT`, with the alias table from §3 (USOIL→CLUSDT and UKOIL→BZUSDT are the
>    two nobody guesses). The feed and the catalogue must both call this one
>    function.
> 3. **The feed.** One `wss://fstream.binance.com/ws` connection:
>    `!bookTicker` for coverage, plus `<sym>@bookTicker` and `<sym>@aggTrade` for
>    the symbols actually on screen, capped at 300 symbols (1024 streams per
>    connection, 200 params per SUBSCRIBE, subscribe in chunks of 150). Last
>    price comes from trades, bid/ask from the book, with a 3 s lead for the
>    trade price. Reconnect on 30 s of silence with backoff capped at 60 s.
>    Drop any single print more than 0.5% from the last one.
> 4. **24 h stats** from `GET /fapi/v1/ticker/24hr` every 10 s (the `!ticker@arr`
>    stream never delivers a frame on this endpoint).
> 5. **History.** Binance klines for crypto; Yahoo's chart API for everything
>    else, with the symbol map in §6, a real User-Agent, and the interval→range
>    caps. Shift the Yahoo series onto the live price with the formula in §6.
>    Cache 60 s.
>
> **Do not:**
> * use Binance **spot** for metals — the PAXG token runs ~0.27% off spot while
>   the XAUUSDT perp runs ~0.05%;
> * use `XAUUSD=X` on Yahoo — it resolves and returns zero intraday bars;
> * let a stale or last-known price reach anything that prices an order;
> * run the feed in more than one worker — elect a leader and mirror quotes
>   through Redis.
>
> **Verify before you tell me it works**, and show me the numbers: contracts
> listed, symbols receiving ticks, updates per second on one hot symbol, and for
> each of XAUUSD / XAGUSD / USOIL / SPY / AAPL the live price next to the number
> on the same Binance futures page. If a symbol has no candles, say so rather
> than shipping an empty chart.
>
> Tell me honestly what this project needs that the document does not cover —
> above all whether anything here must carry real money, because these are
> perpetual futures with 8-hourly funding and a small basis to spot, not
> exchange-traded COMEX contracts.

---

## 9. Re-measuring any of this

```python
# backend/, venv active, against production Redis + Mongo
from app.models.instrument import Instrument
# group instruments by segment → MGET mdlive:{token} → count the `source` field
```

Two seconds end to end. Every number in §1–§3 came from that; if this page and
the system ever disagree, the system is right and this page is stale.
