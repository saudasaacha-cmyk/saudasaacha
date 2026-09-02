#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  SaudaSaacha Broker — production deploy script
#  Runs on the EC2 host. Invoked by GitHub Actions over SSH; can also
#  be run manually:
#      cd /opt/marginplant && bash scripts/deploy.sh
#
#  Smart-rebuild: figures out what actually changed between the previous
#  HEAD and the new origin/main, then rebuilds only the affected piece.
#  A full rebuild forces by setting FORCE_FULL=1.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="/opt/marginplant"
BACKEND_DIR="$REPO_DIR/backend"
USER_DIR="$REPO_DIR/frontend-user"
ADMIN_DIR="$REPO_DIR/frontend-admin"
VENV="$BACKEND_DIR/.venv"

cd "$REPO_DIR"

echo "═══════════════════════════════════════════════════════════════"
echo "  SaudaSaacha deploy — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "═══════════════════════════════════════════════════════════════"

# ── 1) Pull latest ─────────────────────────────────────────────────
PREV_SHA=$(git rev-parse HEAD)
git fetch --quiet origin main
NEW_SHA=$(git rev-parse origin/main)

if [ "$PREV_SHA" = "$NEW_SHA" ] && [ "${FORCE_FULL:-0}" != "1" ]; then
  echo "✓ Already at $NEW_SHA — nothing to do (pass FORCE_FULL=1 to override)"
  exit 0
fi

# Hard reset to origin/main. .env and other gitignored files survive
# because they're not tracked.
git reset --hard origin/main
echo "✓ Pulled $PREV_SHA → $NEW_SHA"

# Detect what changed (forced full rebuild if FORCE_FULL=1)
if [ "${FORCE_FULL:-0}" = "1" ]; then
  CHANGED="ALL"
else
  CHANGED=$(git diff --name-only "$PREV_SHA" "$NEW_SHA" || echo "ALL")
fi

backend_changed=0
user_changed=0
admin_changed=0
backend_deps_changed=0
user_deps_changed=0
admin_deps_changed=0
nginx_changed=0

if [ "$CHANGED" = "ALL" ]; then
  backend_changed=1
  user_changed=1
  admin_changed=1
  backend_deps_changed=1
  user_deps_changed=1
  admin_deps_changed=1
else
  echo "$CHANGED" | grep -q "^backend/"          && backend_changed=1
  echo "$CHANGED" | grep -q "^frontend-user/"    && user_changed=1
  echo "$CHANGED" | grep -q "^frontend-admin/"   && admin_changed=1
  echo "$CHANGED" | grep -q "^backend/requirements.txt$" && backend_deps_changed=1
  echo "$CHANGED" | grep -q "^frontend-user/package-lock.json$" && user_deps_changed=1
  echo "$CHANGED" | grep -q "^frontend-admin/package-lock.json$" && admin_deps_changed=1
  echo "$CHANGED" | grep -q "^deploy/nginx/"     && nginx_changed=1
fi

echo "Changed: backend=$backend_changed user=$user_changed admin=$admin_changed nginx=$nginx_changed"

# ── 2) Backend ─────────────────────────────────────────────────────
if [ "$backend_changed" = "1" ]; then
  echo "── Backend ──"
  if [ "$backend_deps_changed" = "1" ]; then
    echo "  pip install (requirements changed)…"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet -r "$BACKEND_DIR/requirements.txt"
    # Deps (or the systemd unit / env) changed → full restart so the new
    # packages + ExecStart/Environment are actually loaded. A reload won't
    # pick those up.
    echo "  restarting marginplant-backend.service (deps changed)…"
    sudo systemctl restart marginplant-backend
  else
    # Code-only change → graceful ROLLING reload (gunicorn SIGHUP via the
    # unit's ExecReload). Gunicorn re-imports the app, spins up fresh
    # workers and retires the old ones one at a time, so the listen socket
    # is never unbound → no 5xx, WebSockets stay connected, and the
    # leader:feed lock hands off to a standby within its TTL. Falls back to
    # a hard restart if the unit has no ExecReload yet (first deploy of the
    # gunicorn unit).
    echo "  reloading marginplant-backend.service (rolling, code-only)…"
    sudo systemctl reload marginplant-backend || sudo systemctl restart marginplant-backend
  fi
fi

# ── 3) Frontend user ───────────────────────────────────────────────
if [ "$user_changed" = "1" ]; then
  echo "── Frontend user ──"
  cd "$USER_DIR"
  if [ "$user_deps_changed" = "1" ]; then
    echo "  npm ci…"
    npm ci --no-audit --no-fund
  fi
  echo "  building…"
  rm -rf .next
  npm run build
  echo "  reloading PM2 marginplant-user…"
  pm2 reload marginplant-user --update-env
fi

# ── 4) Frontend admin ──────────────────────────────────────────────
if [ "$admin_changed" = "1" ]; then
  echo "── Frontend admin ──"
  cd "$ADMIN_DIR"
  if [ "$admin_deps_changed" = "1" ]; then
    echo "  npm ci…"
    npm ci --no-audit --no-fund
  fi
  echo "  building…"
  rm -rf .next
  npm run build
  echo "  reloading PM2 marginplant-admin…"
  pm2 reload marginplant-admin --update-env
fi

# ── 5) Nginx config sync (if tracked nginx config changed) ─────────
if [ "$nginx_changed" = "1" ] && [ -f "$REPO_DIR/deploy/nginx/marginplant.conf" ]; then
  echo "── Nginx config ──"
  sudo cp "$REPO_DIR/deploy/nginx/marginplant.conf" /etc/nginx/sites-available/marginplant
  sudo nginx -t
  sudo systemctl reload nginx
fi

# ── 6) Healthcheck ─────────────────────────────────────────────────
echo "── Healthcheck ──"
sleep 4
backend_code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:8000/api/v1/user/instruments/search?q=BTC || echo "0")
if [ "$backend_code" = "401" ] || [ "$backend_code" = "200" ]; then
  echo "  ✓ backend OK ($backend_code)"
else
  echo "  ✗ backend FAIL ($backend_code)"
  echo "  Last 20 log lines:"
  sudo journalctl -u marginplant-backend --no-pager -n 20 | sed 's/^/    /'
  exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "✅ Deploy complete: $NEW_SHA"
echo "═══════════════════════════════════════════════════════════════"
