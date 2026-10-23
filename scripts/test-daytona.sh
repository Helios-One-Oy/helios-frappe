#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/proof"
LOG="$ROOT/proof/bench-test-$(date -u +%Y%m%dT%H%M%SZ).log"
if [[ "${DAYTONA_CHILD:-}" == 1 ]]; then
  set -o pipefail
  if ! command -v bench >/dev/null 2>&1; then
    echo "bench is not installed in this Daytona image; installing frappe-bench" | tee "$LOG"
    python3 -m pip install --user frappe-bench >>"$LOG" 2>&1
  fi
  if [[ ! -d "$HOME/frappe-bench/apps/frappe" ]]; then
    bench init --skip-redis-config-generation --frappe-branch version-15 "$HOME/frappe-bench" >>"$LOG" 2>&1
    cd "$HOME/frappe-bench"
    bench get-app --branch version-15 erpnext https://github.com/frappe/erpnext.git >>"$LOG" 2>&1
    bench get-app "$ROOT" >>"$LOG" 2>&1
    bench new-site helios.local --admin-password sample-admin --db-root-password sample-db --no-mariadb-socket >>"$LOG" 2>&1
    bench --site helios.local install-app erpnext >>"$LOG" 2>&1
    bench --site helios.local install-app helios_order_visibility >>"$LOG" 2>&1
  fi
  cd "$HOME/frappe-bench"
  bench --site helios.local run-tests --app helios_order_visibility 2>&1 | tee -a "$LOG"
  exit ${PIPESTATUS[0]}
fi
if ! command -v drun >/dev/null 2>&1; then
  echo "drun is required; this script is intentionally Daytona-only" >&2
  exit 2
fi
 # drun mounts this repository as the command working directory.  Use a
 # relative path so the child does not try to resolve the host's absolute
 # /home/ubuntu path inside the sandbox.
drun --setup "sudo apt-get update -qq && sudo apt-get install -y -qq mariadb-server redis-server" -- env DAYTONA_CHILD=1 bash scripts/test-daytona.sh
