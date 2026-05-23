#!/usr/bin/env bash
# =============================================================================
# TDM – Terrorism Detection & Monitoring System
# Vultr Ubuntu 24.04 LTS x64 – Initial Server Provisioning & Deploy Script
#
# Server has IPv6 only (no IPv4). SSH using brackets around the address:
#   ssh root@[2001:19f0:5c00:4e7d:5400:06ff:fe2e:a9bd]
#
# One-time setup on the server:
#   git clone https://github.com/<your-user>/<your-repo>.git /opt/tdm
#   bash /opt/tdm/scripts/vultr-deploy.sh
#
#   The script will pause on first run so you can fill in /opt/tdm/backend/.env
#   then re-run:  bash /opt/tdm/scripts/vultr-deploy.sh
#
# Subsequent code updates:
#   bash /opt/tdm/scripts/update-app.sh
# =============================================================================

set -euo pipefail
APP_ROOT="/opt/tdm"
APP_USER="tdm"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run this script as root"
[[ -f /etc/os-release ]] && source /etc/os-release
[[ "${VERSION_CODENAME:-}" == "noble" ]] || warn "Script tested on Ubuntu 24.04 (noble). Proceeding anyway."

# ── 0. Verify repo is cloned ─────────────────────────────────────────────────
[[ -d "$APP_ROOT/.git" ]] || die "Repo not found at $APP_ROOT. Clone it first:\n  git clone https://github.com/<user>/<repo>.git $APP_ROOT"
info "Repo found at $APP_ROOT."
git -C "$APP_ROOT" fetch --quiet
git -C "$APP_ROOT" reset --hard origin/main --quiet 2>/dev/null || git -C "$APP_ROOT" reset --hard origin/master --quiet

# ── 1. System packages ───────────────────────────────────────────────────────
info "Updating system packages ..."
apt-get update -qq
apt-get upgrade -y -qq

info "Installing system dependencies ..."
apt-get install -y -qq \
    build-essential git curl wget ca-certificates gnupg \
    python3.12 python3.12-venv python3.12-dev python3-pip \
    nginx certbot python3-certbot-nginx \
    ufw libssl-dev libffi-dev

# ── 2. Node.js 20 LTS ────────────────────────────────────────────────────────
if ! command -v node &>/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 20 ]]; then
    info "Installing Node.js 20 LTS ..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
else
    info "Node.js $(node -v) already installed."
fi

# ── 3. Create system user ────────────────────────────────────────────────────
if ! id "$APP_USER" &>/dev/null; then
    info "Creating system user '$APP_USER' ..."
    useradd --system --shell /bin/bash --home /opt/tdm --no-create-home "$APP_USER"
fi
chown -R "$APP_USER":"$APP_USER" /opt/tdm

# ── 4. Backend: Python virtualenv + dependencies ─────────────────────────────
info "Setting up Python virtual environment ..."
cd "$APP_ROOT/backend"
if [[ ! -d venv ]]; then
    python3.12 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# Create required data directories
mkdir -p "$APP_ROOT/backend/data/uploads" \
         "$APP_ROOT/backend/data/models" \
         "$APP_ROOT/backend/data/datasets"
chown -R "$APP_USER":"$APP_USER" "$APP_ROOT/backend/data"

# Copy ML models if present locally (speeds up first startup)
if [[ -d "$APP_ROOT/backend/data/models" ]]; then
    info "Local ML models directory found — will be used on startup."
fi

# ── 5. Production .env ───────────────────────────────────────────────────────
# .env is NOT in git. On first run we copy .env.example so the user can fill it
# in, then re-run this script.
if [[ ! -f "$APP_ROOT/backend/.env" ]]; then
    cp "$APP_ROOT/backend/.env.example" "$APP_ROOT/backend/.env"
    echo ""
    echo -e "${YELLOW}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  ACTION REQUIRED — fill in production credentials${NC}"
    echo -e "${YELLOW}══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Open the file and set all values:"
    echo "    nano /opt/tdm/backend/.env"
    echo ""
    echo "  Minimum fields to update:"
    echo "    ENVIRONMENT          → production"
    echo "    ALLOWED_HOSTS        → [\"https://shadow-link.dynv6.net\"]"
    echo "    MONGODB_URL          → your Atlas connection string"
    echo "    SECRET_KEY           → run: openssl rand -hex 32"
    echo "    SEED_ADMIN_PASSWORD  → strong password"
    echo "    SMTP_USER / PASSWORD → your Gmail + app password"
    echo "    GOOGLE_CLIENT_ID/SECRET / GOOGLE_REDIRECT_URI"
    echo ""
    echo "  Then re-run:  bash /opt/tdm/scripts/vultr-deploy.sh"
    echo ""
    exit 0
fi
chmod 640 "$APP_ROOT/backend/.env"
chown "$APP_USER":"$APP_USER" "$APP_ROOT/backend/.env"

# ── 6. Frontend: build static assets ─────────────────────────────────────────
info "Building React frontend ..."
cd "$APP_ROOT/frontend"
npm ci --silent
npm run build
chown -R "$APP_USER":"$APP_USER" "$APP_ROOT/frontend/build"

# ── 7. Systemd service ───────────────────────────────────────────────────────
info "Installing systemd service ..."
cp "$APP_ROOT/scripts/systemd/tdm-backend.service" /etc/systemd/system/tdm-backend.service
systemctl daemon-reload
systemctl enable tdm-backend

# ── 8. Nginx ─────────────────────────────────────────────────────────────────
info "Configuring Nginx ..."
rm -f /etc/nginx/sites-enabled/default

# Substitute __APP_ROOT__ placeholder in nginx template
sed "s|__APP_ROOT__|${APP_ROOT}|g" \
    "$APP_ROOT/scripts/nginx/tdm.conf" \
    > /etc/nginx/sites-available/tdm

ln -sf /etc/nginx/sites-available/tdm /etc/nginx/sites-enabled/tdm
nginx -t
systemctl enable nginx
systemctl reload nginx

# ── 9. SSL via Let's Encrypt ─────────────────────────────────────────────────
DOMAIN="${TDM_DOMAIN:-shadow-link.dynv6.net}"
info "Obtaining Let's Encrypt certificate for $DOMAIN ..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --email "${CERTBOT_EMAIL:-admin@${DOMAIN}}" --redirect || \
    warn "Certbot failed — run manually: certbot --nginx -d $DOMAIN"

# ── 10. Firewall ─────────────────────────────────────────────────────────────
info "Configuring UFW firewall ..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# ── 11. Start backend ────────────────────────────────────────────────────────
info "Starting TDM backend service ..."
systemctl start tdm-backend
systemctl status tdm-backend --no-pager

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  TDM deployment complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
if [[ -n "$DOMAIN" ]]; then
    echo "  Frontend :  https://${DOMAIN}"
    echo "  API docs  :  (disabled in production)"
else
    echo "  Frontend :  https://shadow-link.dynv6.net"
    echo "  API health:  https://shadow-link.dynv6.net/health"
fi
echo ""
echo "  Logs     :  journalctl -u tdm-backend -f"
echo "  Restart  :  systemctl restart tdm-backend"
echo "  Update   :  bash /opt/tdm/scripts/update-app.sh"
echo ""
if [[ ! -f "$APP_ROOT/backend/.env" ]] || grep -q "CHANGE-ME\|your-" "$APP_ROOT/backend/.env" 2>/dev/null; then
    echo -e "${YELLOW}  ACTION REQUIRED: Edit /opt/tdm/backend/.env with production credentials${NC}"
fi
