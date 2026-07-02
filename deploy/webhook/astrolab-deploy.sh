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

echo "[deploy] backend: deps + migrate"
runuser -u astrolab -- bash -lc '
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
