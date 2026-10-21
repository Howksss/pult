#!/usr/bin/env bash
set -euo pipefail
umask 077

compose_file="${COMPOSE_FILE:-$(dirname "$0")/../docker-compose.yml}"
backup_dir="${BACKUP_DIR:-/var/backups/pult}"
retention_days="${RETENTION_DAYS:-14}"
database="${POSTGRES_DB:-pult}"
user="${POSTGRES_USER:-pult}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="${backup_dir}/${database}_${stamp}.dump"

mkdir -p "$backup_dir"
docker compose -f "$compose_file" exec -T db pg_dump --format=custom --compress=6 --no-owner -U "$user" "$database" > "$file.part"
docker compose -f "$compose_file" exec -T db pg_restore --list < "$file.part" > /dev/null
mv "$file.part" "$file"
find "$backup_dir" -name "${database}_*.dump" -mtime +"$retention_days" -delete
echo "$file"
