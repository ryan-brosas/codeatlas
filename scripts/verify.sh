#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

(
  cd "$ROOT/analysis"
  uv sync --locked
  uv run ruff format --check src tests
  uv run ruff check src tests
  uv run mypy src tests
  uv run pytest
)

(
  cd "$ROOT/web"
  npm run verify
)
