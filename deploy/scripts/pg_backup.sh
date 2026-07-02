#!/usr/bin/env bash
# Nightly astrolab DB dump with 30-day rotation (matches the backup-retention
# promise in PRIVACY_MODEL.md §4). Reads the DB URL from /etc/astrolab/env.
set -euo pipefail

BACKUP_DIR=/var/backups/astrolab
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

# pg_dump connects locally as the astrolab role (peer/local auth on nikam).
pg_dump -Fc astrolab > "$BACKUP_DIR/astrolab-$STAMP.dump"

# Rotate: keep 30 days.
find "$BACKUP_DIR" -name 'astrolab-*.dump' -mtime +30 -delete

echo "[pg_backup] wrote astrolab-$STAMP.dump; rotated >30d"
