# Proof artifacts

Evidence produced by the test commands, never invented product claims.

* `version-16/` and `version-15/` each hold one clean-install run of [`scripts/test-daytona.sh`](../scripts/test-daytona.sh) (`FRAPPE_BRANCH=version-16|version-15`) in a Daytona sandbox: a fresh Frappe bench with ERPNext, this app installed, the demo fixture from [`helios_order_visibility/tests/live_seed.py`](../helios_order_visibility/tests/live_seed.py), and a real-browser run of [`scripts/live-browser.py`](../scripts/live-browser.py).
* `bench-test-*.log` is the full run log; `live/http-ui.log` the browser checks; `live/db-after-ui.txt` the Purchase Order rows read back from the database after the supplier submitted the guest form; `screenshots/` the 1280 px and 390 px captures.
* The site runs in `Europe/Helsinki` so the pages and stored datetimes are shown to follow System Settings, not the server clock. Fixture dates are relative to the site's today.
* Capability tokens are redacted from committed files.
