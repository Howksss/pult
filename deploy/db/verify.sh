#!/usr/bin/env bash
set -euo pipefail

source_db="${1:?usage: verify.sh <source-db> <restored-db>}"
restored_db="${2:?usage: verify.sh <source-db> <restored-db>}"
pg_bin="${PG_BIN:-}"

query() {
  "${pg_bin}psql" -X -A -t -v ON_ERROR_STOP=1 -d "$1" -c "$2"
}

schema() {
  "${pg_bin}pg_dump" --schema-only --no-owner --no-privileges "$1" \
    | grep -v -e '^--' -e '^\\restrict' -e '^\\unrestrict' -e '^$' \
    | sha256sum | cut -c1-16
}

report() {
  if [[ "$2" == "$3" ]]; then
    printf '%-16s %12s  ok\n' "$1" "$2"
  else
    printf '%-16s %12s  expected %s\n' "$1" "$2" "$3"
    failed=1
  fi
}

failed=0
report schema "$(schema "$restored_db")" "$(schema "$source_db")"

tables="$(query "$restored_db" "select tablename from pg_tables where schemaname = 'public' and tablename <> 'alembic_version' order by tablename")"
for table in $tables; do
  actual="$(query "$restored_db" "select count(*) from $table")"
  has_id="$(query "$restored_db" "select count(*) from information_schema.columns
    where table_schema = 'public' and table_name = '$table' and column_name = 'id'")"
  if [[ "$has_id" == "1" ]]; then
    last_id="$(query "$restored_db" "select coalesce(max(id), 0) from $table")"
    expected="$(query "$source_db" "select count(*) from $table where id <= $last_id")"
  else
    expected="$(query "$source_db" "select count(*) from $table")"
  fi
  report "$table" "$actual" "$expected"
done

report alembic_version \
  "$(query "$restored_db" "select version_num from alembic_version")" \
  "$(query "$source_db" "select version_num from alembic_version")"

exit "$failed"
