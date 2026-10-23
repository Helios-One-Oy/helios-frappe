# Helios Order Visibility for ERPNext

Helios Order Visibility adds supplier PO confirmation, customer order tracking, a Supplier OTD Script Report, and a late-lines workspace shortcut to ERPNext. It uses Frappe `doc_events`, a daily scheduler hook, signed HMAC capability tokens, and app-owned custom fields. It does not replace Frappe login or patch ERPNext core.

The public links contain only a short-lived capability token. The server stores only its SHA-256 digest, checks the token purpose, expiry, signature, database status, and reference before reading or writing anything. Supplier replies are parsed from a constrained subject/body format and matched to the supplier email on the PO. Repeated identical confirmations are idempotent; conflicting decisions are rejected.

## Quickstart

```bash
bench get-app https://github.com/Helios-One-Oy/helios-frappe.git
bench --site <site> install-app helios_order_visibility
bench --site <site> migrate
```

Open **Helios Settings** and set the expiry windows and optional public base URL. The app creates its roles and custom fields during migration. Submit a Purchase Order, Sales Order, or Delivery Note to generate the corresponding link. The sample records in [`fixtures/sample_manufacturing_data.json`](fixtures/sample_manufacturing_data.json) are fictional and are not loaded automatically.

## Compatibility

The app declares Frappe and ERPNext `>=15.0.0,<17.0.0` in [`pyproject.toml`](pyproject.toml). This is the repository's compatibility declaration; it is not a claim that every release in that range has been live-tested. Run the Daytona/bench check before publishing a release. See [`docs/compatibility.md`](docs/compatibility.md).

## Tests

The deterministic harness has no Frappe or database dependency:

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest
```

Use the marketplace test wrapper to run the deterministic suite and, when a bench, `drun`, or `frun` runner is available, the live bench suite:

```bash
scripts/test-marketplace.sh
```

The live script writes output to `proof/bench-test-<UTC timestamp>.log`. Do not treat an unrun log as proof. See [`docs/operations.md`](docs/operations.md) for email routing, expiry, permissions, and upgrade notes, [`docs/compatibility.md`](docs/compatibility.md) for the version declaration, and [`marketplace/README.md`](marketplace/README.md) for the prepared but unpublished listing package.
