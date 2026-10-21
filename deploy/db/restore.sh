#!/usr/bin/env bash
set -euo pipefail

dump="${1:?usage: restore.sh <dump-file> [target-database]}"
target="${2:-${PGDATABASE:?PGDATABASE is required}_restore}"
pg_bin="${PG_BIN:-}"

"${pg_bin}dropdb" --if-exists "$target"
"${pg_bin}createdb" "$target"
"${pg_bin}pg_restore" --no-owner --exit-on-error --dbname="$target" "$dump"
echo "restored into $target"
