#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  SachchaSauda Broker — production deploy script
#  Runs on the EC2 host. Invoked by GitHub Actions over SSH; can also
#  be run manually:
#      cd /opt/saudasaacha && bash scripts/deploy.sh
#
#  Smart-rebuild: figures out what actually changed between the previous
#  HEAD and the new origin/main, then rebuilds only the affected piece.
#  A full rebuild forces by setting FORCE_FULL=1.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# This script is run by root (GitHub Actions over SSH) but the app is
# served by `sauda`, and the two halves of the work need different
# accounts:
#
#   • systemctl / nginx need root, which root already has — `sauda` has
#     no sudo rights for them on this host, only for the two branding
#     scripts.
#   • npm build and PM2 need `sauda`. A root deploy wrote 388 root-owned
#     files into frontend-user/.next and then died on `pm2 reload`: root's
#     PM2 daemon owns no processes, so it answered "Process or Namespace
#     not found", `set -e` took the script down, and the entire admin
#     frontend section silently never ran — a deploy that printed a
#     successful build and shipped nothing.
#
# So: `as_app` for anything that writes into this tree or touches PM2.
# Same trap as the root-owned .git objects — whatever root writes here is
# something `sauda` can no longer rewrite.
APP_USER="sauda"
if [ "$(id -un)" = "$APP_USER" ]; then
  as_app() { "$@"; }
else
  as_app() { sudo -u "$APP_USER" -H "$@"; }
fi

REPO_DIR="/opt/saudasaacha"
BACKEND_DIR="$REPO_DIR/backend"
USER_DIR="$REPO_DIR/frontend-user"
ADMIN_DIR="$REPO_DIR/frontend-admin"
VENV="$BACKEND_DIR/.venv"

cd "$REPO_DIR"

echo "═══════════════════════════════════════════════════════════════"
echo "  SachchaSauda deploy — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "═══════════════════════════════════════════════════════════════"

# ── 1) Pull latest ─────────────────────────────────────────────────
PREV_SHA=$(git rev-parse HEAD)
as_app git fetch --quiet origin main
NEW_SHA=$(git rev-parse origin/main)

if [ "$PREV_SHA" = "$NEW_SHA" ] && [ "${FORCE_FULL:-0}" != "1" ]; then
  echo "✓ Already at $NEW_SHA — nothing to do (pass FORCE_FULL=1 to override)"
  exit 0
fi

# Hard reset to origin/main. .env and other gitignored files survive
# because they're not tracked.
as_app git reset --hard origin/main
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
    # The venv was created by `uv venv`, which does NOT put pip inside it —
    # $VENV/bin/pip does not exist and neither does `python -m pip`. Use uv
    # when it is there, and fall back to pip for a venv made the old way.
    if command -v uv >/dev/null 2>&1; then
      as_app uv pip install --python "$VENV/bin/python" -q -r "$BACKEND_DIR/requirements.txt"
    else
      as_app "$VENV/bin/python" -m pip install --quiet --upgrade pip
      as_app "$VENV/bin/python" -m pip install --quiet -r "$BACKEND_DIR/requirements.txt"
    fi
    # Deps (or the systemd unit / env) changed → full restart so the new
    # packages + ExecStart/Environment are actually loaded. A reload won't
    # pick those up.
    echo "  restarting saudasaacha-backend.service (deps changed)…"
    sudo systemctl restart saudasaacha-backend
  else
    # Code-only change → graceful ROLLING reload (gunicorn SIGHUP via the
    # unit's ExecReload). Gunicorn re-imports the app, spins up fresh
    # workers and retires the old ones one at a time, so the listen socket
    # is never unbound → no 5xx, WebSockets stay connected, and the
    # leader:feed lock hands off to a standby within its TTL. Falls back to
    # a hard restart if the unit has no ExecReload yet (first deploy of the
    # gunicorn unit).
    echo "  reloading saudasaacha-backend.service (rolling, code-only)…"
    sudo systemctl reload saudasaacha-backend || sudo systemctl restart saudasaacha-backend
  fi
fi

# ── 3) Frontend user ───────────────────────────────────────────────
if [ "$user_changed" = "1" ]; then
  echo "── Frontend user ──"
  cd "$USER_DIR"
  if [ "$user_deps_changed" = "1" ]; then
    echo "  npm ci…"
    as_app npm ci --no-audit --no-fund
  fi
  # Stamp the service worker with this commit BEFORE building.
  #
  # `public/sw.js` scopes every runtime cache to a hardcoded VERSION and
  # its own comment promises that "bumping VERSION evicts every old
  # runtime cache on activate" — but nothing ever bumped it. It sat at
  # v9 across every deploy since the brand rename, so the cached app
  # shell was never evicted: on a slow connection the 2-second navigation
  # race hands the user that stale shell, which references the old
  # chunk hashes, which are themselves cache-first stored. The result is
  # a deploy that went out cleanly and a user who keeps seeing the old
  # app with nothing to tell either of them why.
  #
  # Done here rather than in the app because `sw.js` is a static file
  # with no build-time substitution, and because a constant that must be
  # hand-bumped every release is a constant that will not be.
  if [ -f public/sw.js ]; then
    as_app sed -i -E "s/^const VERSION = \".*\";/const VERSION = \"sachchasauda-pwa-${NEW_SHA:0:12}\";/" public/sw.js
    echo "  sw.js VERSION → sachchasauda-pwa-${NEW_SHA:0:12}"
  fi

  echo "  building…"
  # Build beside the live .next, then swap. Deleting .next first left the
  # running server serving a folder that no longer existed for the whole
  # build — every asset 404'd and the site rendered unstyled.
  as_app rm -rf .next-build .next-old
  as_app env NEXT_DIST_DIR=.next-build npm run build
  as_app mv .next .next-old 2>/dev/null || true
  as_app mv .next-build .next
  echo "  reloading PM2 saudasaacha-user…"
  as_app pm2 reload saudasaacha-user --update-env
  as_app rm -rf .next-old
fi

# ── 4) Frontend admin ──────────────────────────────────────────────
if [ "$admin_changed" = "1" ]; then
  echo "── Frontend admin ──"
  cd "$ADMIN_DIR"
  if [ "$admin_deps_changed" = "1" ]; then
    echo "  npm ci…"
    as_app npm ci --no-audit --no-fund
  fi
  echo "  building…"
  # Build beside the live .next, then swap. Deleting .next first left the
  # running server serving a folder that no longer existed for the whole
  # build — every asset 404'd and the site rendered unstyled.
  as_app rm -rf .next-build .next-old
  as_app env NEXT_DIST_DIR=.next-build npm run build
  as_app mv .next .next-old 2>/dev/null || true
  as_app mv .next-build .next
  echo "  reloading PM2 saudasaacha-admin…"
  as_app pm2 reload saudasaacha-admin --update-env
  as_app rm -rf .next-old
fi

# ── 5) Nginx config sync (if tracked nginx config changed) ─────────
if [ "$nginx_changed" = "1" ] && [ -f "$REPO_DIR/deploy/nginx/saudasaacha.conf" ]; then
  echo "── Nginx config ──"
  sudo cp "$REPO_DIR/deploy/nginx/saudasaacha.conf" /etc/nginx/sites-available/saudasaacha
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
  sudo journalctl -u saudasaacha-backend --no-pager -n 20 | sed 's/^/    /'
  exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "✅ Deploy complete: $NEW_SHA"
echo "═══════════════════════════════════════════════════════════════"
