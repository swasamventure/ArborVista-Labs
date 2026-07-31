#!/usr/bin/env sh
set -eu
: "${DATABASE_URL:?Set DATABASE_URL}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
file="$BACKUP_DIR/arbor_vista_$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl --file="$file"
echo "Created $file"
