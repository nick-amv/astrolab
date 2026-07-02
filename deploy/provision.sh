#!/usr/bin/env bash
# One-time (idempotent) provisioning for astrolab on nikam. Run as root.
#
# Required env:
#   ASTROLAB_DB_PASSWORD        password for the astrolab Postgres role
#   ASTROLAB_WEBHOOK_SECRET     HMAC secret shared with the GitHub webhook
# Optional env:
#   ASTROLAB_OAUTH_TOKEN        CLAUDE_CODE_OAUTH_TOKEN (blank OK in Wave 0)
#
# Safe to re-run: every step checks before acting.
set -euo pipefail

: "${ASTROLAB_DB_PASSWORD:?set ASTROLAB_DB_PASSWORD}"
: "${ASTROLAB_WEBHOOK_SECRET:?set ASTROLAB_WEBHOOK_SECRET}"
OAUTH_TOKEN="${ASTROLAB_OAUTH_TOKEN:-}"
REPO=/opt/astrolab

echo "== 1. system user =="
id -u astrolab &>/dev/null || useradd --system --create-home --shell /bin/bash astrolab

echo "== 2. postgres role + db (owner = astrolab, NOT postgres) =="
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='astrolab'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE ROLE astrolab LOGIN PASSWORD '${ASTROLAB_DB_PASSWORD}'"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='astrolab'" | grep -q 1 \
  || sudo -u postgres createdb -O astrolab astrolab

echo "== 3. directories =="
install -d -o astrolab -g astrolab "$REPO"
install -d -o astrolab -g astrolab /var/backups/astrolab
install -d -m 750 /etc/astrolab

echo "== 4. /etc/astrolab/env (only if missing) =="
if [ ! -f /etc/astrolab/env ]; then
  cat > /etc/astrolab/env <<EOF
ASTROLAB_ENVIRONMENT=prod
ASTROLAB_DATABASE_URL=postgresql+psycopg://astrolab:${ASTROLAB_DB_PASSWORD}@localhost:5432/astrolab
ASTROLAB_CORS_ORIGINS=https://astrolab.nikam.dev
ASTROLAB_RETENTION_DAYS=90
ASTROLAB_REPORT_TTL_DAYS=180
ASTROLAB_LLM_BACKEND=max_cli
ASTROLAB_CLAUDE_CODE_OAUTH_TOKEN=${OAUTH_TOKEN}
ORIGIN=https://astrolab.nikam.dev
PUBLIC_API_BASE=https://astrolab.nikam.dev/api
EOF
  chmod 640 /etc/astrolab/env
  echo "  wrote /etc/astrolab/env"
else
  echo "  exists, left untouched"
fi

echo "== 5. deploy ssh key for private repo (read-only) =="
if [ ! -f /home/astrolab/.ssh/id_ed25519 ]; then
  runuser -u astrolab -- ssh-keygen -t ed25519 -N "" -f /home/astrolab/.ssh/id_ed25519 -C "nikam-astrolab-deploy"
  runuser -u astrolab -- bash -lc 'ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null'
  echo "  >>> ADD THIS AS A DEPLOY KEY on nick-amv/astrolab (read-only):"
  cat /home/astrolab/.ssh/id_ed25519.pub
  echo "  (then re-run this script to clone)"
fi

echo "== 6. clone / update repo =="
if [ ! -d "$REPO/.git" ]; then
  if runuser -u astrolab -- git clone git@github.com:nick-amv/astrolab.git "$REPO"; then
    echo "  cloned"
  else
    echo "  clone failed — is the deploy key added? Skipping build."
    exit 0
  fi
else
  runuser -u astrolab -- bash -lc "cd $REPO && git fetch --quiet origin && git reset --hard origin/main --quiet"
fi

echo "== 7. backend venv + migrate =="
runuser -u astrolab -- bash -lc "
  cd $REPO/backend &&
  { [ -d .venv ] || python3 -m venv .venv; } &&
  .venv/bin/pip install --quiet --upgrade pip &&
  .venv/bin/pip install --quiet -e . &&
  .venv/bin/alembic upgrade head"

echo "== 8. frontend build =="
runuser -u astrolab -- bash -lc "cd $REPO/frontend && npm ci --no-audit --no-fund --silent && npm run build"

echo "== 9. systemd units =="
cp "$REPO"/deploy/systemd/*.service "$REPO"/deploy/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now astrolab-api astrolab-web
systemctl enable --now astrolab-retention.timer astrolab-backup.timer

echo "== 10. deploy hook script =="
cp "$REPO/deploy/webhook/astrolab-deploy.sh" /usr/local/bin/astrolab-deploy.sh
chmod +x /usr/local/bin/astrolab-deploy.sh

echo "== DONE =="
echo "Remaining manual steps (see deploy/README.md):"
echo "  - add the astrolab-deploy block to /etc/webhook/hooks.json (secret above)"
echo "  - add the astrolab.nikam.dev block + _astrolab_deploy route to /etc/caddy/Caddyfile"
echo "  - reload caddy + restart hub-webhook"
echo "  - add the GitHub webhook (https://hub.nikam.dev/_astrolab_deploy, the secret)"
