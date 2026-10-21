#!/usr/bin/env bash
set -euo pipefail

api="${API_URL:-http://localhost:8000}"
web="${WEB_URL:-http://localhost:8080}"

for _ in $(seq 1 60); do
  if curl -fsS "$api/api/health" > /dev/null 2>&1 && curl -fsS "$web/" > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "health: $(curl -fsS "$api/api/health")"

curl -fsS "$web/" | grep -q '<div id="root">'
echo "frontend: index.html served"

code="$(curl -s -o /dev/null -w '%{http_code}' "$web/api/v1/projects/999/graph")"
type="$(curl -s -o /dev/null -w '%{content_type}' "$web/api/v1/projects/999/graph")"
[[ "$code" == "404" && "$type" == application/problem+json* ]]
echo "proxy: /api via nginx returns $code $type"

if [[ "${EXPECT_BLOCKS:-}" != "" ]]; then
  curl -fsS "$web/api/v1/projects/1/graph" | python3 -c "
import json, sys
graph = json.load(sys.stdin)
blocks = {block['name']: block['status'] for block in graph['blocks']}
assert len(blocks) == int(sys.argv[1]), blocks
print('graph:', blocks)
" "$EXPECT_BLOCKS"
fi
