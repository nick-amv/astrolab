#!/usr/bin/env bash
# Deploy hook for astrolab. Installed at /usr/local/bin/astrolab-deploy.sh and
# invoked by the webhook listener (:9099) on a verified push to origin/main.
# Runs as root; drops to the astrolab user for git + build steps.
set -e
cd /opt/astrolab
echo "[deploy $(date -Iseconds)] fetching…"
runuser -u astrolab -- git fetch --quiet origin
LOCAL=$(runuser -u astrolab -- git rev-parse HEAD)
REMOTE=$(runuser -u astrolab -- git rev-parse origin/main)
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[deploy] nothing to do ($LOCAL)"
    exit 0
fi
runuser -u astrolab -- git reset --hard origin/main --quiet

# Self-update versioned host config (this script + systemd units) so infra
# changes ship on push too. Takes effect from the next deploy.
cp /opt/astrolab/deploy/webhook/astrolab-deploy.sh /usr/local/bin/astrolab-deploy.sh
chmod +x /usr/local/bin/astrolab-deploy.sh /opt/astrolab/deploy/scripts/pg_backup.sh
cp /opt/astrolab/deploy/systemd/*.service /opt/astrolab/deploy/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload

echo "[deploy] backend: deps + migrate"
# Source the env so alembic connects with the real DB URL (not the default).
runuser -u astrolab -- bash -lc '
  set -a && . /etc/astrolab/env && set +a &&
  cd /opt/astrolab/backend &&
  .venv/bin/pip install --quiet -e . &&
  .venv/bin/alembic upgrade head'

echo "[deploy] frontend: install + build"
runuser -u astrolab -- bash -lc '
  cd /opt/astrolab/frontend &&
  npm ci --no-audit --no-fund --silent &&
  npm run build'

echo "[deploy] restarting services"
systemctl restart astrolab-api astrolab-web
sleep 3
systemctl is-active astrolab-api astrolab-web
echo "[deploy] done — now at $(runuser -u astrolab -- git rev-parse --short HEAD)"
