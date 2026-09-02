# SaudaSaacha Broker — Indian B-Book Stock Trading Platform

Production-grade, scalable-to-1M-users Indian stock trading platform (Zerodha / Upstox / Angel One class).
**B-Book broker model**: all trades match internally; external APIs are used **only** for price feeds.

---

## Repository layout

```
.
├── backend/         FastAPI + MongoDB + Redis + Celery (Phase 1: foundation done)
├── frontend-user/   Next.js 14 user web app (port 3000)
└── frontend-admin/  Next.js 14 super-admin web app (port 3001)
```

Two separate frontends so user and admin can be deployed at independent
hostnames (`app.saudasaacha.com` / `admin.saudasaacha.com`) with their own
CORS origins, bundles, and security postures (admin has stricter CORS,
mandatory 2FA, IP allow-list, API key).

---

## Phase status

The build is staged across 7 phases as specified.

| # | Phase                                         | Status |
|---|-----------------------------------------------|:------:|
| 1 | **Foundation** — auth, models, core infra     | **✓ done** |
| 2 | Admin core — segment settings, wizard, payin-out | pending |
| 3 | Market data — instruments, WS feed, marketwatch, charts | pending |
| 4 | Trading — validator, internal matching, positions, holdings | pending |
| 5 | Wallet — manual deposit/withdrawal, ledger    | pending |
| 6 | Reports — PDF / Excel / CSV                   | pending |
| 7 | Polish — notifications, audit, backup, settings | pending |

---

## What Phase 1 ships

### Backend (`backend/`)
- **Core infra** (`app/core/`): typed Pydantic config, Motor + Beanie MongoDB lifecycle, async Redis client (cache + pub/sub + sliding-window rate limit + idempotency), structured JSON logging, custom exception hierarchy + global handlers, JWT (15 min access / 7 day refresh w/ Redis allow-list rotation), bcrypt rounds=12, TOTP 2FA, FastAPI dependencies (`CurrentUser`, `CurrentAdmin`, `SuperAdmin`).
- **All 27 Beanie collection models** with indexes ready for sharding, Decimal128 money fields, TTL indexes (audit, notifications), text search on instruments, embedded snapshots on orders/trades.
- **Utility modules**: Decimal money helpers + INR formatting, IST/market-hours helpers, OTP issue/verify with attempt-cap, Indian-format validators (PAN, IFSC, Aadhaar w/ Verhoeff, mobile, GST).
- **Pydantic schemas**: auth, user, common envelopes (`APIResponse`, paged + cursor), admin auth.
- **Services**: `auth_service` (login, refresh w/ rotation, logout, 2FA setup/enable/disable, password change/reset, lockout after 5 fails), `user_service` (creation, code generation, hierarchy walks), `audit_service` (fire-and-forget event logging).
- **API endpoints**: `/api/v1/user/auth/*`, `/api/v1/user/users/me`, `/api/v1/admin/auth/*`. Both flows distinct; admin guarded by API key + IP allow-list + mandatory 2FA.
- **Bootstrap seeding** (idempotent): super admin, 20 segment-settings global rows, 4 default templates (Bronze/Silver/Gold/VIP), default brokerage plan, default company bank, deposit/withdrawal rules, platform settings, NSE holidays.
- **Celery app** with task routing and beat schedule scaffold (tasks themselves added in later phases).
- `main.py` with CORS, Gzip, request-id middleware, security headers, Prometheus `/metrics`, Sentry (optional), `/health` + `/health/db` + `/health/redis`.

### Frontend-user (`frontend-user/`, port 3000)
- Next.js 14 App Router + TypeScript + Tailwind dark theme matching spec exactly (`#0a0a0a` bg, `#10b981` buy/profit, `#ef4444` sell/loss).
- shadcn-style primitives: `Button`, `Input`, `Card`, `Label`. Toaster (Sonner). React Query w/ devtools.
- Zustand auth store with localStorage persist + hydration.
- Axios client with auto-refresh + single-flight refresh + uniform `ApiError` unwrap.
- Auth pages: **login** (with 2FA prompt fall-through), **register** (PAN/mobile validation), **forgot-password** (2-step OTP), **2FA enrollment** (provisioning URI display).
- Authenticated layout: collapsible `Sidebar`, `TopBar` with search, `IndicesTicker`, `StatusBar` with IST clock + market open/closed indicator + WS connection status.
- `/dashboard` skeleton with 6 summary cards, top-mover preview placeholders, watchlist preview.

### Frontend-admin (`frontend-admin/`, port 3001)
- Same stack, separate app, indexed `noindex,nofollow`.
- Axios client always sends `X-Admin-Api-Key` from env; refresh hits `/admin/auth/refresh`.
- **Admin login** with mandatory 2FA (zod-enforced 6-digit code).
- Sidebar with grouped navigation (Overview / Users / Trading / Money / Reports / System) covering every admin module path called out in the spec.
- Top bar with audit-warning banner.
- `/dashboard` skeleton with 8 stat cards (Users, Volume, Revenue, Pending approvals, …) + risk-monitor + system-health placeholders.

---

## Running locally

### Prereqs
- Python 3.11+
- Node 20+
- MongoDB 7+ (replica set required for transactions in later phases — single-node ok for Phase 1)
- Redis 7+

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then edit JWT_SECRET, ADMIN_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>
- Default super admin: `admin@saudasaacha.com` / `Admin@123` (must change password on first login). Admin login also requires 2FA — enroll via the user app first, then sign in to the admin app.

### Frontend-user

```bash
cd frontend-user
cp .env.example .env.local
npm install
npm run dev          # http://localhost:3000
```

### Frontend-admin

```bash
cd frontend-admin
cp .env.example .env.local      # set NEXT_PUBLIC_ADMIN_KEY to match backend ADMIN_API_KEY
npm install
npm run dev          # http://localhost:3001
```

---

## Architectural notes

- **Money**: `bson.Decimal128` end-to-end; `app/utils/decimal_utils.py` is the only place floats are tolerated (and only at the I/O boundary).
- **Settings hierarchy**: GLOBAL → TEMPLATE → USER OVERRIDE (highest wins). Resolver lives in `services/segment_settings_service.py` (Phase 2) and caches per `(user_id, segment_type)` in Redis with 5-min TTL.
- **WS fanout**: Redis pub/sub channels (`user:{id}`, `market:tick`, `admin:events`) so multiple FastAPI instances broadcast consistently. Wired in Phase 3.
- **Sharding-ready**: `orders`, `trades`, `wallet_transactions`, `audit_logs`, `notifications` carry compound `(user_id, …)` indexes appropriate for `user_id`-shard.
- **Audit**: `audit_logs` has a 1-year TTL via `expires_at`. Switch to a MongoDB time-series collection if write rate exceeds ~10k/s.
- **Two frontends, one API**: lets us deploy admin behind a separate ingress with IP allow-list and stricter rate limits without affecting user latency.

---

## Security posture

- bcrypt rounds = 12; `auth_service` re-hashes on next successful login if cost is raised.
- Failed-login lockout (5 attempts → 15 min lock) on user accounts.
- Admin endpoints gated by **all of**: valid JWT + admin role + `X-Admin-Api-Key` header + IP allow-list (when configured) + mandatory 2FA.
- JWT refresh tokens use Redis allow-list keyed by JTI; logout deletes the JTI; refresh rotates JTI.
- Rate limits: 5/min auth, 100/min default, 300/min trading — sliding-window in Redis Lua.
- Security headers: CSP-friendly defaults, HSTS in production, frame-deny, referrer-policy, permissions-policy.
- CORS allow-listed to two specific origins (user app + admin app).
Step 1 — Redis start kar (naya PowerShell window):


& "C:\Users\vibho\redis-portable\bin\redis-server.exe" --port 6379

Step 2 — Backend start kar (alag PowerShell window):

cd "D:\saudasaacha_ind\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
