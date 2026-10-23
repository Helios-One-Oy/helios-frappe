#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== deterministic tests =="
PYTHON_BIN="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then PYTHON_BIN="$ROOT/.venv/bin/python"; fi
"$PYTHON_BIN" -m pytest

# A caller can point this at an already-created bench. This is the only path
# that claims a live Frappe result on the current machine.
if [[ -n "${FRAPPE_BENCH:-}" && -x "${FRAPPE_BENCH}/env/bin/bench" ]]; then
  SITE="${FRAPPE_SITE:-$(find "$FRAPPE_BENCH/sites" -mindepth 1 -maxdepth 1 -type d ! -name assets -printf '%f\n' | head -1)}"
  [[ -n "$SITE" ]] || { echo "FRAPPE_BENCH has no site; skipping live test"; exit 0; }
  (cd "$FRAPPE_BENCH" && bench --site "$SITE" run-tests --app helios_order_visibility)
  exit 0
fi

# drun uses Daytona and automatically overflows to frun when the shared
# Daytona pool is full. The child script creates the bench and writes a dated
# proof log. Set DRUN_BACKEND=fly to force frun when needed.
if command -v drun >/dev/null 2>&1; then
  exec scripts/test-daytona.sh
fi

echo "No bench, drun, or frun runner is available; deterministic tests passed." >&2
