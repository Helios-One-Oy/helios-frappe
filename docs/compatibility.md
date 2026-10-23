# Compatibility and release evidence

The app declares the following dependency range in [`pyproject.toml`](../pyproject.toml):

| Component | Declared range | Evidence in this repository |
| --- | --- | --- |
| Frappe Framework | `>=15.0.0,<17.0.0` | `[tool.bench.frappe-dependencies]` |
| ERPNext | `>=15.0.0,<17.0.0` | `[tool.bench.frappe-dependencies]` and `required_apps` in [`hooks.py`](../helios_order_visibility/hooks.py) |
| Python | `>=3.10` | `[project]` in `pyproject.toml` |

The range is a declaration for packaging and review. The deterministic tests do not start Frappe, MariaDB, Redis, or an ERPNext site. A live compatibility result is valid only when [`scripts/test-daytona.sh`](../scripts/test-daytona.sh) produces a dated `proof/bench-test-*.log` for the exact dependency branches used. The current repository has no such live log, so this package does not claim current-stable runtime validation.

Before a release, record the exact Frappe and ERPNext branches, the site version, and the test log path in the release notes. Re-run the live test when Frappe Cloud's current stable version changes.
