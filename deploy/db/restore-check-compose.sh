#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-$(dirname "$0")/../docker-compose.yml}"
backup_dir="${BACKUP_DIR:-/var/backups/pult}"
database="${POSTGRES_DB:-pult}"
user="${POSTGRES_USER:-pult}"
target="${CHECK_DB:-${database}_restore_check}"
file="${1:-$(ls -t "$backup_dir"/"${database}"_*.dump | head -1)}"

db() {
  docker compose -f "$compose_file" exec -T -e PGUSER="$user" db "$@"
}

echo "copy: $(basename "$file"), $(stat -c %s "$file") bytes"
start="$(date +%s)"
db dropdb --if-exists "$target" < /dev/null
db createdb "$target" < /dev/null
db pg_restore --no-owner --exit-on-error --dbname="$target" < "$file"
echo "restore took $(($(date +%s) - start)) s"

status=0
db bash -s -- "$database" "$target" < "$(dirname "$0")/verify.sh" || status=$?
db dropdb "$target" < /dev/null
echo "verify exit $status, $target dropped"
exit "$status"
