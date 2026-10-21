#!/usr/bin/env bash
set -euo pipefail

source_db="${1:?usage: verify.sh <source-db> <restored-db>}"
restored_db="${2:?usage: verify.sh <source-db> <restored-db>}"
pg_bin="${PG_BIN:-}"
tables=(app_user project project_member block block_link block_scope health_check check_result agent_task task_message change_request deployment audit_event)

count() {
  "${pg_bin}psql" -X -A -t -d "$1" -c "select count(*) from $2"
}

failed=0
for table in "${tables[@]}"; do
  expected="$(count "$source_db" "$table")"
  actual="$(count "$restored_db" "$table")"
  if [[ "$expected" == "$actual" ]]; then
    printf '%-16s %10s  ok\n' "$table" "$actual"
  else
    printf '%-16s %10s  expected %s\n' "$table" "$actual" "$expected"
    failed=1
  fi
done

version_source="$("${pg_bin}psql" -X -A -t -d "$source_db" -c "select version_num from alembic_version")"
version_restored="$("${pg_bin}psql" -X -A -t -d "$restored_db" -c "select version_num from alembic_version")"
printf '%-16s %10s  %s\n' "alembic_version" "$version_restored" "$([[ "$version_source" == "$version_restored" ]] && echo ok || echo mismatch)"
[[ "$version_source" == "$version_restored" ]] || failed=1

exit "$failed"
