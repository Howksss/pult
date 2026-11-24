#!/usr/bin/env bash
set -euo pipefail
umask 077

offsite_env="${OFFSITE_ENV:-/root/.config/pult/offsite.env}"
if [[ -r "$offsite_env" ]]; then
  set -a
  source "$offsite_env"
  set +a
fi

compose_file="${COMPOSE_FILE:-$(dirname "$0")/../docker-compose.yml}"
backup_dir="${BACKUP_DIR:-/var/backups/pult}"
retention_days="${RETENTION_DAYS:-14}"
weekly_retention_days="${WEEKLY_RETENTION_DAYS:-56}"
weekly_day="${WEEKLY_DAY:-7}"
offsite="${OFFSITE_REMOTE:-}"
database="${POSTGRES_DB:-pult}"
user="${POSTGRES_USER:-pult}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="${backup_dir}/${database}_${stamp}.dump"

mkdir -p "$backup_dir/weekly"
docker compose -f "$compose_file" exec -T db pg_dump --format=custom --compress=6 --no-owner -U "$user" "$database" > "$file.part"
docker compose -f "$compose_file" exec -T db pg_restore --list < "$file.part" > /dev/null
mv "$file.part" "$file"

if [[ "$(date -u +%u)" == "$weekly_day" || "${FORCE_WEEKLY:-0}" == "1" ]]; then
  ln -f "$file" "$backup_dir/weekly/"
fi

if [[ -n "$offsite" ]]; then
  rclone copy "$file" "$offsite/daily/"
  if [[ -e "$backup_dir/weekly/$(basename "$file")" ]]; then
    rclone copy "$file" "$offsite/weekly/"
  fi
  rclone delete --min-age "${retention_days}d" "$offsite/daily/"
  rclone delete --min-age "${weekly_retention_days}d" "$offsite/weekly/"
fi

find "$backup_dir" -maxdepth 1 -name "${database}_*.dump" -mtime +"$retention_days" -delete
find "$backup_dir/weekly" -name "${database}_*.dump" -mtime +"$weekly_retention_days" -delete
echo "$file"
