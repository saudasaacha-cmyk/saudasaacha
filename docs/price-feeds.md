# Where every price comes from

Measured on production, 2026-10-08. Three live feeds, no others — MetaAPI and
Infoway are gone.

| Feed | Serves | How it subscribes |
|---|---|---|
| **Zerodha Kite** | Every Indian segment (NSE, NFO, BFO, MCX) | WS, per numeric instrument token, on demand |
| **Binance USDT-M futures** | Crypto, metals, energy, world indices, US stocks | One socket, whole exchange (`!bookTicker`), plus a fast lane per watched symbol |
| **Binance spot** | Eight legacy `CRYPTO_*` crypto rows | WS per pair |

Each live quote is mirrored to Redis as `mdlive:{token}` and carries the
`source` field the table below was built from, so this page can be re-measured
rather than believed:

```bash
redis-cli --raw get mdlive:XAUUSD | python -m json.tool   # → "source": "binance_futures"
```

## By segment

| Segment | Active | Source | Examples |
|---|---:|---|---|
| CRYPTO_SPOT | 528 | binance_futures (520) + binance spot (8) | BTCUSD, ETHUSD, 1000000MOG |
| STOCKS | 193 | **binance_futures** | AAPL, NVDA, MSTR, MU, SOXL |
| NFO_OPTION | 336 | zerodha | NIFTY/BANKNIFTY/stock CE+PE |
| BFO_OPTION | 226 | zerodha | SENSEX CE+PE |
| MCX_OPTION | 222 | zerodha | CRUDEOIL 8100 CE/PE |
| NSE_EQUITY | 147 | zerodha | RELIANCE, HDFCBANK |
| MCX_FUTURE | 111 | zerodha | GOLD26DECFUT, SILVER26DECFUT |
| NFO_FUTURE | 49 | zerodha | NIFTY26OCTFUT |
| INDICES | 14 | **binance_futures** | SPY, QQQ, IWM, GDX, EWJ |
| COMMODITIES | 8 | **binance_futures** | XAUUSD, XAGUSD, USOIL, NATGAS |
| BSE_EQUITY / BFO_FUTURE | 5 | zerodha | thin, often no live tick |

"Active" is the catalogue count, not how many are ticking at any moment: an
Indian contract only ticks while its exchange is open, and an illiquid one
trades a few times an hour.

## The eight COMMODITIES rows — what they really are

This is the part worth knowing: **gold and silver do not come from COMEX.**
They are Binance USDT-M perpetuals.

| Our symbol | Binance contract | Live price seen |
|---|---|---|
| XAUUSD | XAUUSDT | 4122.61 |
| XAGUSD | XAGUSDT | 58.86 |
| XPTUSD | XPTUSDT | 1653.60 |
| XPDUSD | XPDUSDT | 1138.56 |
| USOIL | CLUSDT (WTI) | 92.16 |
| UKOIL | BZUSDT (Brent) | 104.06 |
| NATGAS | NATGASUSDT | 3.34 |
| COPPER | COPPERUSDT | 6.67 |

INDICES and STOCKS work the same way — `SPY` is `SPYUSDT`, `AAPL` is
`AAPLUSDT`. Anything not in the table above resolves by rule: exact symbol,
else `+T`, else `+USDT` (`backend/app/services/binance_futures_service.py`).

**These are perpetual futures, not spot and not the exchange-traded contract.**
Funding settles every 8 h and the perp carries a small basis — measured at
~0.05% on gold. Close to COMEX, never identical to it. If a client compares
our gold against a COMEX screen they will see a few dollars of difference, and
that is the instrument, not a bug.

## Candles are not from the same place as the tick

A chart shows two different things and they come from two different sources:

| Instrument | Live tick | History (candles) |
|---|---|---|
| Crypto | Binance | Binance klines |
| Metals / energy | Binance perp | Yahoo **COMEX/NYMEX front month** — GC=F, SI=F, PL=F, PA=F, CL=F, BZ=F, NG=F |
| Indices / US stocks | Binance perp | Yahoo — ^GSPC, ^NDX, …, plain ticker for stocks |
| Indian | Zerodha WS | Kite historical API |

Yahoo's contract trades a little away from our live price, so
`_align_candles_to_live` shifts the whole series by (live − last close) before
it reaches the chart: the real intraday shape, on the price the BUY/SELL
buttons use. Yahoo's `XAUUSD=X` form is deliberately unused — it resolves but
serves zero intraday bars.

## Re-measuring this page

```python
# backend/, with the venv active
from app.models.instrument import Instrument
# group instruments by segment, MGET mdlive:{token}, count the `source` field
```

The full script lives in the commit that added this file; it takes about two
seconds against production Redis.
