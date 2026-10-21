#!/usr/bin/env bash
set -euo pipefail

backup_dir="${BACKUP_DIR:-./backups}"
retention_days="${RETENTION_DAYS:-14}"
pg_bin="${PG_BIN:-}"
database="${PGDATABASE:?PGDATABASE is required}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="${backup_dir}/${database}_${stamp}.dump"

mkdir -p "$backup_dir"
"${pg_bin}pg_dump" --format=custom --compress=6 --no-owner --file="$file" "$database"
"${pg_bin}pg_restore" --list "$file" > /dev/null
find "$backup_dir" -name "${database}_*.dump" -mtime +"$retention_days" -delete
echo "$file"
