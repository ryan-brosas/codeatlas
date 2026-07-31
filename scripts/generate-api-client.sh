#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMA_FILE="$(mktemp)"
trap 'rm -f "$SCHEMA_FILE"' EXIT

(
  cd "$ROOT/analysis"
  uv run python - "$SCHEMA_FILE" <<'PY'
import json
import sys

from codeatlas_analysis.api import app

with open(sys.argv[1], "w", encoding="utf-8") as schema_file:
    json.dump(app.openapi(), schema_file, sort_keys=True)
PY
)

mkdir -p "$ROOT/web/src/lib/api"
"$ROOT/web/node_modules/.bin/openapi-typescript" "$SCHEMA_FILE" \
  --output "$ROOT/web/src/lib/api/generated.d.ts"
