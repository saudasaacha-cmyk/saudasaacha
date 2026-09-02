# Zerodha Auto-Login — Production Deployment

Daily-scheduled Kite Connect access-token refresh. Drives the Kite OAuth +
TOTP screen with a headless Playwright Chromium so the admin doesn't have
to manually login every weekday.

This guide covers ONLY the server-side deployment. Local dev is irrelevant —
the feature only runs in production where the daily 07:00 IST trigger
fires against the real Kite endpoints.

---

## 1. What was added

### Backend
- `backend/app/utils/crypto.py` — AES-256-GCM encrypt/decrypt for credentials at rest
- `backend/app/models/zerodha_auto_login.py` — singleton Beanie document for encrypted creds + scheduler state
- `backend/app/services/zerodha_auto_login.py` — Playwright login flow with 3-layer request_token capture + WebSocket-safe token handoff
- `backend/app/services/zerodha_auto_login_scheduler.py` — daily IST loop with Redis SETNX leader lock
- `backend/app/api/v1/admin/zerodha_auto_login.py` — 5 super-admin-only endpoints
- Wired into `backend/app/main.py` lifespan (start/stop) and `backend/app/api/v1/admin/__init__.py` (router)
- Model registered in `backend/app/core/database.py`
- New env var `ZERODHA_CREDS_KEY` added to `backend/app/core/config.py`
- New dependency `playwright>=1.45.0,<2` in `backend/requirements.txt`

### Frontend (admin)
- `frontend-admin/lib/api.ts` — `ZerodhaAutoLoginAPI` namespace
- `frontend-admin/components/zerodha/CredentialsModal.tsx` — credentials capture dialog
- `frontend-admin/components/zerodha/AutoLoginPanel.tsx` — main status + controls card
- Integrated into `frontend-admin/app/(admin)/zerodha/page.tsx`

---

## 2. EC2 deployment steps (one-time setup)

SSH into the production server first.

### 2.1 Generate a per-environment encryption key

NEVER reuse the dev key in production. Generate a fresh one on the server:

```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Output looks like: `KqB8...PnQ=` (44 chars).

### 2.2 Add it to the production .env

```bash
sudo nano /etc/sachchasauda/.env   # or wherever your prod env lives
```

Add this line (paste the key generated above):

```bash
ZERODHA_CREDS_KEY=KqB8...PnQ=
```

Save and exit. **Do not commit this key to git.** Verify file permissions are 600:

```bash
sudo chmod 600 /etc/sachchasauda/.env
sudo chown <backend-user>:<backend-user> /etc/sachchasauda/.env
```

### 2.3 Install Python deps

```bash
cd /path/to/sachchasauda_ind_web/backend
sudo -u <backend-user> .venv/bin/pip install -r requirements.txt
```

Make sure you run this **as the same user that runs the backend systemd unit**
(usually `ubuntu` or a dedicated `sachchasauda` user). Otherwise the
backend won't find the new packages.

### 2.4 Install Chromium for Playwright

```bash
sudo -u <backend-user> .venv/bin/playwright install chromium
sudo -u <backend-user> .venv/bin/playwright install-deps chromium   # Linux only — installs apt deps
```

`install-deps` requires sudo and pulls down ~30 MB of shared libraries
(libnss3, libnspr4, libdbus-1, etc.) that Chromium needs to run headless.
If you skip this step, browser launch will fail with:

```
Error: browserType.launch: Host system is missing dependencies
```

### 2.5 Verify everything imports

```bash
sudo -u <backend-user> .venv/bin/python -c "
from app.services.zerodha_auto_login import zerodha_auto_login
from app.services.zerodha_auto_login_scheduler import zerodha_auto_login_loop
from app.utils.crypto import encrypt, decrypt
c, iv = encrypt('test')
print('crypto roundtrip:', decrypt(c, iv))
"
```

Should print `crypto roundtrip: test`.

### 2.6 Restart the backend service

```bash
sudo systemctl restart saudasaacha-backend
sudo journalctl -u saudasaacha-backend -f --since '1 minute ago'
```

Look for these log lines on startup:

```
zerodha_auto_login_scheduler_started
app_started ...
```

If you see `playwright not installed` in the scheduler logs, repeat 2.3 +
2.4 making sure you used the correct backend user.

---

## 3. First-time admin setup (one-time)

This is the operator workflow — done once via the admin panel.

### 3.1 Get the TOTP secret from Kite

You MUST have the base32 TOTP secret. Kite doesn't show the existing one
for security — you have to reset TOTP to get a fresh secret.

1. Go to https://kite.zerodha.com → Profile → Password & Security
2. Find the "External 2FA TOTP" section → click **Reset TOTP**
3. Confirm with Authy + password
4. On the new QR screen, click **"Can't scan?"** / **"Manual entry"**
5. Copy the 16–32 char base32 string (looks like `JBSWY3DPEHPK3PXP6X7K…`)
6. **Add the same secret to Authy** before completing the verification —
   old Authy entry is now dead. Add Account → Enter Code Manually → paste secret
7. Verify the new TOTP works by completing the Kite setup screen

Store the secret in a password manager (Bitwarden / 1Password). Don't
screenshot it, don't email it, don't paste it into general notes apps.

### 3.2 Save creds in the admin panel

1. Open the admin panel → **Zerodha Connect** page (super-admin only)
2. Scroll to the **Auto-login (daily)** card
3. Click **Save credentials** → fill in:
   - **Kite Client ID** (e.g. `ZK1234`)
   - **Password** (the same one you use to login to kite.zerodha.com)
   - **TOTP Secret** (from step 3.1)
4. Click **Save credentials** — toast confirms "Credentials saved"

### 3.3 Test the login

Before enabling the daily scheduler, do a manual test:

1. Click **Test login now**
2. Watch the status card. After 10–25 seconds you'll see one of:
   - ✅ `Login successful in XX.X s` → all good, proceed
   - ❌ `Login failed at "stage_name": …` → check the troubleshooting section below

### 3.4 Set the schedule + enable

1. Set **Daily schedule** (default 07:00 IST) — this is 2h 15m before the
   09:15 IST market open, giving you a buffer to manually fallback if the
   3 automatic retries all fail
2. Click **Update time** to save
3. Click **Enable** to flip the scheduler ON

Status pill turns green: "Enabled". Done.

---

## 4. WebSocket safety guarantees

Auto-login is wired so the existing KiteTicker pool stays healthy across
the daily token refresh. The flow is:

1. `refresh_now()` acquires a Redis SETNX lock (`zerodha_auto_login:refresh_lock`, 5 min TTL) — prevents two workers from running the browser simultaneously
2. Sets `zerodha._self_heal_paused = True` — pauses the 30-s self-heal loop so it doesn't race the new login
3. Calls `await zerodha.disconnect_ws()` — explicitly tears down every existing `KiteTicker` connection on the OLD token (clean `Connection.close()` + 403-resilient ticker map cleanup)
4. Runs the Playwright login → gets the new `request_token` via 3-layer capture (`page.on("request")` observer + `page.route()` abort + DB freshness fallback)
5. Calls the existing `zerodha.generate_session(request_token)` — saves the new access_token to `ZerodhaSettings` AND triggers `_post_login_ws_kickoff` which spawns a fresh ticker pool on the new token
6. Always (`finally:`) re-arms `zerodha._self_heal_paused = False` — even on partial failure, the 30-s self-heal loop can recover from there
7. Releases the Redis lock

This means even if step 5 raises an exception, the next 30-s self-heal
tick will see no live ticker and call `connect_ws(force=True)` to bring
it back. The token refresh is idempotent — Kite tolerates multiple
`generate_session` calls fine.

### What protects against the KiteTicker 403 storm

Kite allows ONLY ONE WebSocket per access token. When we issue a new
token, every old WS instance gets a 403 close. The existing
`on_close` handler in `zerodha_service.py:1326-1360` already prunes
zombie entries on 403/1006, so the old tickers vanish cleanly without
leaving stale entries in `_token_to_ws`.

Our `disconnect_ws()` call in step 3 short-circuits that — old connections
close BEFORE the new token exists, so the prune path is never even hit.

### What protects against Twisted/asyncio bridging

The `KiteTicker.on_ticks` callback runs in Twisted's reactor thread.
The existing `zerodha_service.py:1401-1407` already handles this with
`asyncio.run_coroutine_threadsafe(publish(...), self._main_loop)`. We
don't touch this path. Auto-login only adds REST-side calls; the WS
tick stream is unaffected.

---

## 5. Daily scheduler behavior

- Wakes every 60 s (cheap — just one Mongo find_one for `is_enabled`)
- Fires the login only when:
  - `is_enabled == True` (admin toggled on)
  - Current IST time within 60 s of `schedule_time_ist`
  - Not a weekend (Sat=5, Sun=6)
  - Not an Indian trading holiday (`TradingHoliday` collection)
  - This worker won the `zerodha_auto_login:scheduler_leader` lock (10 min TTL)
- Retries up to 3× with 5 min gap between attempts on failure
- After all retries exhausted: dispatches a `NotificationLevel.DANGER`
  Notification to every super-admin so they get the bell-icon alert
- Records `last_fired_iso_date` in-memory to prevent double-fire on the same day

---

## 6. Troubleshooting

Failures surface in the admin panel with the stage name. Map of stages
to root causes:

| Stage | Meaning | Fix |
|---|---|---|
| `precheck` | Kite API key not configured | Set it in the existing Zerodha settings page first |
| `decrypt` | Wrong `ZERODHA_CREDS_KEY` (e.g. key was rotated) | Re-save credentials with the new key, or restore the old key |
| `import` | `playwright` package not installed OR `playwright install chromium` not run on this host | Re-run section 2.3 + 2.4 with the correct backend user |
| `navigate` | Kite login URL did not load in 20s | Server's outbound HTTP to `kite.zerodha.com` is broken — check firewall / DNS |
| `userid` | Username/password form not interactive | Kite changed their login page; selectors need updating in `zerodha_auto_login.py:_run_login_flow` |
| `password` | Kite showed a wrong-password error banner | The saved password is incorrect or your Kite account is locked |
| `totp_page` | TOTP screen didn't appear after username/password | Likely wrong password (Kite shows error before TOTP) — overlaps with `password` stage |
| `totp_submit` | TOTP code rejected OR no redirect | Most common cause: **server clock drift > 30s**. Check `timedatectl status` — `System clock synchronized: yes` must show. Less common: TOTP secret in DB differs from Authy (re-save them together) |
| `redirect` | Never landed on /callback | Kite OAuth callback URL in your Kite app settings doesn't match your `ZerodhaSettings.redirectUrl` |
| `session` | `generate_session()` REST call to Kite failed | Token race — usually self-recovers via the layer-3 fallback. If consistent, check Kite API secret |
| `lock` | Another auto-login is already in progress | Wait 5 min; lock auto-expires |

Screenshots on TOTP failure are saved to `/tmp/zerodha_totp_fail_*.png`
on Linux (configurable in `_run_login_flow`). SSH in and download to
diagnose UI changes.

### Clock sync check

If TOTP keeps failing despite a correct secret:

```bash
timedatectl status
# Should show:
#   System clock synchronized: yes
#   NTP service: active

# If not:
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
```

### Tail backend logs during a test login

```bash
sudo journalctl -u saudasaacha-backend -f | grep -E 'zerodha_auto_login|zerodha_scheduler|callback'
```

You should see, in order:
```
zerodha_auto_login_callback_seen
zerodha_auto_login_callback_aborted
... access_token saved ...
zerodha_post_login_ws_kickoff_failed   # only if WS already alive — ignore
zerodha_WS-1_connected                  # fresh ticker on new token
```

---

## 7. Manual fallback

If auto-login is broken for any reason, the existing manual login flow
is **completely untouched**:

1. Open admin → Zerodha Connect
2. Click **Login with Kite** (existing button, not the new auto-login card)
3. Complete the manual Kite + Authy flow
4. Token refreshed exactly as before

Auto-login can stay disabled while you fix whatever broke. There's no
ambient state to clean up — the scheduler just sits idle when `is_enabled`
is False.

---

## 8. Security checklist

Before going live:

- [ ] `ZERODHA_CREDS_KEY` is a fresh per-environment key, not the dev one
- [ ] `.env` file is `chmod 600`, owned by the backend service user
- [ ] Kite API key used has `no_trading` permission (orders can't be placed even if creds leak — defense in depth, doesn't affect B-book operations)
- [ ] TOTP secret was entered ONCE in the admin panel, then cleared from clipboard / password manager session
- [ ] Backup admin code stored separately (Kite generates these — needed if you ever lose access to both Authy and the new TOTP secret)

---

## 9. Files changed (for git review)

```
Backend:
  app/api/v1/admin/__init__.py                   # router registration
  app/api/v1/admin/zerodha_auto_login.py         # NEW — 5 endpoints
  app/core/config.py                              # ZERODHA_CREDS_KEY field
  app/core/database.py                            # register new model
  app/main.py                                     # lifespan task wiring
  app/models/zerodha_auto_login.py               # NEW — Beanie singleton
  app/services/zerodha_auto_login.py             # NEW — Playwright flow
  app/services/zerodha_auto_login_scheduler.py   # NEW — daily IST loop
  app/utils/crypto.py                             # NEW — AES-256-GCM
  requirements.txt                                # + playwright

Frontend (admin):
  app/(admin)/zerodha/page.tsx                    # import + render panel
  components/zerodha/AutoLoginPanel.tsx           # NEW — status card
  components/zerodha/CredentialsModal.tsx         # NEW — capture dialog
  lib/api.ts                                      # ZerodhaAutoLoginAPI namespace

Local-only (DO NOT commit):
  .env                                            # ZERODHA_CREDS_KEY value
```
