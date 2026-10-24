# Frappe Cloud Marketplace submission package

Submitted through the free Frappe Cloud publisher route (no fee, no separate developer agreement for free apps). The structured fields are in [`listing.json`](listing.json). The repository is MIT licensed and contains no customer data.

## Listing copy

**Title:** Helios Order Visibility  
**Summary (40–80 characters):** Supplier confirmations and customer order tracking for ERPNext  
**Category:** Manufacturing / Operations  
**Publisher:** Helios One Oy  
**License:** MIT  
**Support:** support@heliosone.fi  

Supplier PO confirmation uses an expiring signed link or a constrained reply handled by an authenticated mailbox. A confirmation writes the supplier decision and schedule date to the Purchase Order and its open lines. Customer tracking links expose a filtered Sales Order or Delivery Note snapshot. Buyers get a supplier OTD Script Report and a late-lines workspace shortcut.

The pages suppliers and customers open show the installing company's own name and records, with dates in the site's time zone and date format. Demo data exists only in `fixtures/` and `helios_order_visibility/tests/` and is never loaded on a site. Public links require the site's Frappe `encryption_key`; raw tokens are never stored. Do not describe the app as certified or claim customer deployments before they exist.

## Current official requirements checked 2026-10-23

The official publishing guide says the repository must be public, GitHub-owned by the publisher, open source under MIT or a GPL-compatible license, uniquely named, compatible with the current stable Frappe/ERPNext release, and backed by passing CI. The listing needs a square logo of at least 200×200 pixels, five URLs (website, support, documentation, terms, privacy), a 40–80 character one-sentence summary, a separate long description without install steps, screenshots/videos, and a submitted release. The review flow also requires publisher setup and a manual “Mark app ready for review” action. This repository is prepared for those fields; no listing action has been taken.

Sources: [Marketplace overview](https://docs.frappe.io/cloud/marketplace), [publish an app](https://docs.frappe.io/cloud/marketplace/publishing-an-app-to-marketplace), [publishing guidelines](https://docs.frappe.io/cloud/marketplace/marketplace-guidelines), [app authoring and CI guidelines](https://docs.frappe.io/cloud/marketplace/app-authoring-guidelines), and [Marketplace terms](https://cloud.frappe.io/marketplace/terms). The terms incorporate publishing guidelines that can change, so re-check the portal immediately before submission.

## Evidence map

| Requirement/evidence | File |
| --- | --- |
| App metadata, public MIT license, version | [`../pyproject.toml`](../pyproject.toml), [`../setup.py`](../setup.py), [`../LICENSE`](../LICENSE) |
| Install/update hooks and migration-safe setup | [`../helios_order_visibility/hooks.py`](../helios_order_visibility/hooks.py), [`../helios_order_visibility/patches/v1_0.py`](../helios_order_visibility/patches/v1_0.py) |
| Roles, DocTypes, report and workspace | [`../helios_order_visibility/doctype/`](../helios_order_visibility/doctype/), [`../helios_order_visibility/report/`](../helios_order_visibility/report/), [`../helios_order_visibility/workspace/`](../helios_order_visibility/workspace/) |
| Signed guest capability and permissions | [`../helios_order_visibility/permissions.py`](../helios_order_visibility/permissions.py), [`../helios_order_visibility/services/tokens.py`](../helios_order_visibility/services/tokens.py) |
| Real-bench test command | [`../scripts/test-daytona.sh`](../scripts/test-daytona.sh) |
| Deterministic test harness | [`../tests/test_pure.py`](../tests/test_pure.py) |
| Demo fixture (tests only) | [`../fixtures/sample_manufacturing_data.json`](../fixtures/sample_manufacturing_data.json) |

Live evidence: `scripts/test-daytona.sh` runs a clean bench with ERPNext on `version-16` (current stable) and `version-15`; logs and 1280/390 px screenshots are under `proof/version-16/` and `proof/version-15/`.
