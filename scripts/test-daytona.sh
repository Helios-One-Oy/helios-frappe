#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# FRAPPE_BRANCH selects the Frappe/ERPNext release line (version-16 is the
# current stable; version-15 is still supported). Each line writes its own
# proof directory so both runs can be kept side by side.
FRAPPE_BRANCH="${FRAPPE_BRANCH:-version-16}"
export HELIOS_PROOF_ROOT="$ROOT/proof/${FRAPPE_BRANCH}"
mkdir -p "$HELIOS_PROOF_ROOT"
LOG="$HELIOS_PROOF_ROOT/bench-test-$(date -u +%Y%m%dT%H%M%SZ).log"
if [[ "${DAYTONA_CHILD:-}" == 1 ]]; then
  set -o pipefail
  # `pip --user` places bench under ~/.local/bin in a clean Daytona image.
  # Keep the script self-contained so a fresh sandbox has the same PATH as a
  # developer shell.
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v bench >/dev/null 2>&1; then
    echo "bench is not installed in this Daytona image; installing frappe-bench" | tee "$LOG"
    python3 -m pip install --user frappe-bench >>"$LOG" 2>&1
  fi
  # Frappe v15 needs Python <=3.13 and v16 needs 3.14; record the choice.
  if [[ "$FRAPPE_BRANCH" == version-15 ]]; then
    PYTHON_BIN="$(command -v python3.13 || command -v python3)"
  else
    PYTHON_BIN="$(command -v python3.14 || command -v python3)"
  fi
  echo "frappe_branch=$FRAPPE_BRANCH" | tee -a "$LOG"
  "$PYTHON_BIN" --version | tee -a "$LOG"
  node --version | tee -a "$LOG"
  echo "python_bin=$PYTHON_BIN" | tee -a "$LOG"
  sudo service mariadb start >>"$LOG" 2>&1 || true
  sudo service redis-server start >>"$LOG" 2>&1 || true
  # `bench init --skip-redis-config-generation` still points Frappe's queue
  # workers at the standard bench ports.  Start those disposable Redis
  # instances so ERPNext migrations can enqueue cleanup jobs during install.
  redis-server --port 11000 --daemonize yes >>"$LOG" 2>&1 || true
  redis-server --port 12000 --daemonize yes >>"$LOG" 2>&1 || true
  redis-server --port 13000 --daemonize yes >>"$LOG" 2>&1 || true
  # Debian/MariaDB images create root with unix_socket authentication.  Bench
  # connects to localhost over TCP during site creation, so give the ephemeral
  # test root a known password inside this disposable Daytona machine.
  sudo mariadb -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'sample-db'; FLUSH PRIVILEGES;" >>"$LOG" 2>&1 || true
  for i in $(seq 1 30); do
    if mysqladmin ping -h 127.0.0.1 --silent >>"$LOG" 2>&1; then break; fi
    sleep 1
  done
  if [[ ! -d "$HOME/frappe-bench/apps/frappe" ]]; then
    bench init --skip-redis-config-generation --skip-assets --python "$PYTHON_BIN" --frappe-branch "$FRAPPE_BRANCH" "$HOME/frappe-bench" >>"$LOG" 2>&1
    cd "$HOME/frappe-bench"
    bench get-app --branch "$FRAPPE_BRANCH" erpnext >>"$LOG" 2>&1
    # bench get-app's local-path parser assumes a hosted org/repo and crashes
    # on a filesystem path with recent bench releases.  Install this private
    # app from the mounted source tree explicitly, which is also repeatable in
    # a clean Daytona image.
    rm -rf apps/helios_order_visibility
    cp -a "$ROOT" apps/helios_order_visibility
    # bench may leave the final app name without a trailing newline.
    # Prefix with one so the private app cannot concatenate with erpnext.
    printf '\n%s\n' helios_order_visibility >> sites/apps.txt
    "$HOME/frappe-bench/env/bin/pip" install --quiet -e apps/helios_order_visibility >>"$LOG" 2>&1
    # Daytona's MariaDB root account authenticates through its local socket;
    # letting bench use the socket avoids a TCP root-auth mismatch.
    bench new-site helios.local --admin-password sample-admin --db-root-password sample-db >>"$LOG" 2>&1
    bench --site helios.local install-app erpnext >>"$LOG" 2>&1
    bench --site helios.local install-app helios_order_visibility >>"$LOG" 2>&1
    # Some minimal bench images omit encryption_key from new-site config;
    # public integration links require one for HMAC signing.  This value is
    # disposable and exists only inside the clean Daytona proof site.
    bench --site helios.local set-config encryption_key "m3-daytona-fictional-encryption-key" >>"$LOG" 2>&1
    bench --site helios.local set-config allow_tests true >>"$LOG" 2>&1
    # Install-app does not run the app's after_migrate hook on every bench
    # release; materialize the integration's Custom Fields and roles explicitly
    # before creating submitted ERPNext documents.
    bench --site helios.local execute helios_order_visibility.patches.v1_0.ensure_custom_fields >>"$LOG" 2>&1
  fi
  cd "$HOME/frappe-bench"
  mkdir -p "$HELIOS_PROOF_ROOT/live" "$HELIOS_PROOF_ROOT/screenshots"
  echo "clean_install_http_ui=BEGIN" | tee -a "$LOG"
  HELIOS_PROOF_DIR="$HELIOS_PROOF_ROOT/live" bench --site helios.local execute helios_order_visibility.tests.live_seed.run 2>&1 | tee "$HELIOS_PROOF_ROOT/live/seed-console.log" | tee -a "$LOG"
  bench --site helios.local serve --port 8000 >"$HELIOS_PROOF_ROOT/live/frappe-server.log" 2>&1 &
  SERVER_PID=$!
  trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
  for i in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8000/helios/confirm >/dev/null 2>&1; then break; fi
    sleep 1
  done
  python3 "$ROOT/scripts/live-browser.py" | tee -a "$LOG"
  bench --site helios.local execute helios_order_visibility.tests.live_seed.db_snapshot 2>&1 | tee "$HELIOS_PROOF_ROOT/live/db-after-ui.txt" | tee -a "$LOG"
  # Proof artifacts are committed for review; remove replayable capability
  # values while leaving routes and status codes intact.
  find "$HELIOS_PROOF_ROOT/live" -type f \( -name '*.log' -o -name '*.json' -o -name '*.html' -o -name '*.txt' \) -print0 | xargs -0 -r sed -E -i \
    -e 's/(token=)[^&" <>]+/\1REDACTED_TOKEN/g' \
    -e 's/(name="token" value=")[^"]+/\1REDACTED_TOKEN/g' \
    -e 's/(name="csrf" value=")[^"]+/\1REDACTED_TOKEN/g' \
    -e 's/("(supplier_token|customer_token|late_token)"[[:space:]]*:[[:space:]]*")[^"]+/\1REDACTED_TOKEN/g'
  echo "screenshots=PASS" | tee -a "$LOG"
  set +e
  bench --site helios.local run-tests --app helios_order_visibility 2>&1 | tee -a "$LOG"
  test_status=${PIPESTATUS[0]}
  set -e
  if [[ "$test_status" -ne 0 ]]; then
    echo "clean_install_http_ui=FAIL" | tee -a "$LOG"
    exit "$test_status"
  fi
  echo "clean_install_http_ui=PASS" | tee -a "$LOG"
  exit 0
fi
if ! command -v drun >/dev/null 2>&1; then
  echo "drun is required; this script is intentionally Daytona-only" >&2
  exit 2
fi
# drun mounts this repository as the command working directory.  Use a
# relative path so the child does not try to resolve the host's absolute
# /home/ubuntu path inside the sandbox.  drun uses Daytona and overflows to
# Fly only when the Daytona pool is full.
# Node 24 (required by Frappe v16) comes from the official tarball so both
# release lines build with the same toolchain.
drun --snapshot daytona-large --setup "sudo apt-get update -qq && sudo apt-get install -y -qq mariadb-server redis-server cron python3.13 python3.13-dev python3.13-venv python3-pip build-essential pkg-config libmariadb-dev chromium curl xz-utils && (sudo apt-get install -y -qq python3.14 python3.14-dev python3.14-venv || true) && curl -fsSL https://nodejs.org/dist/v24.11.0/node-v24.11.0-linux-x64.tar.xz | sudo tar -xJ -C /usr/local --strip-components=1 && sudo npm install -g yarn@1.22.22 && python3 -m pip install --user --break-system-packages playwright" -- env DAYTONA_CHILD=1 FRAPPE_BRANCH="$FRAPPE_BRANCH" bash scripts/test-daytona.sh
