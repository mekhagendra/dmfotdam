#!/usr/bin/env bash
# =============================================================================
# TDM – Application Update Script
# Run this after uploading a new version of the code to /opt/tdm
#
# Usage (on Vultr server, as root or tdm):
#   bash /opt/tdm/scripts/update-app.sh
# =============================================================================

set -euo pipefail
APP_ROOT="/opt/tdm"
APP_USER="tdm"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }

# ── 0. Pull latest code from git ─────────────────────────────────────────────
info "Pulling latest code from git ..."
git -C "$APP_ROOT" fetch --quiet
git -C "$APP_ROOT" reset --hard origin/main --quiet 2>/dev/null || \
    git -C "$APP_ROOT" reset --hard origin/master --quiet

# ── 1. Python dependencies ───────────────────────────────────────────────────
info "Updating Python dependencies ..."
source "$APP_ROOT/backend/venv/bin/activate"
pip install --upgrade pip -q
pip install -r "$APP_ROOT/backend/requirements.txt" -q
deactivate

# ── 2. Frontend build ────────────────────────────────────────────────────────
info "Rebuilding React frontend ..."
cd "$APP_ROOT/frontend"
npm ci --silent
npm run build
chown -R "$APP_USER":"$APP_USER" "$APP_ROOT/frontend/build"

# ── 3. Reload backend (zero-downtime within single-worker model) ─────────────
info "Reloading TDM backend ..."
systemctl reload-or-restart tdm-backend
sleep 3
systemctl is-active tdm-backend && info "Backend is running." || warn "Backend may have failed – check: journalctl -u tdm-backend -n 50"

# ── 4. Reload Nginx ───────────────────────────────────────────────────────────
info "Reloading Nginx ..."
nginx -t && systemctl reload nginx

info "Update complete."
