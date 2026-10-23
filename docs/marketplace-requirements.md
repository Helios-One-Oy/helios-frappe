# Frappe Cloud Marketplace requirement record

Access date: **2026-10-23 UTC**.

The official pages used for this package are:

* [Marketplace overview](https://docs.frappe.io/cloud/marketplace)
* [Publish an app on the Frappe Cloud Marketplace](https://docs.frappe.io/cloud/marketplace/publishing-an-app-to-marketplace)
* [Guidelines for publishing an app](https://docs.frappe.io/cloud/marketplace/marketplace-guidelines)
* [App authoring guidelines](https://docs.frappe.io/cloud/marketplace/app-authoring-guidelines)
* [Marketplace terms](https://cloud.frappe.io/marketplace/terms)

## Evidence checklist

| Official requirement | Evidence or remaining action | File |
| --- | --- | --- |
| Public GitHub repository owned by publisher | Repository remote and publishing status are external checks; this package does not submit it | `marketplace/README.md` |
| MIT or GPL-compatible open-source license | MIT license and app metadata | [`LICENSE`](../LICENSE), [`helios_order_visibility/hooks.py`](../helios_order_visibility/hooks.py), [`pyproject.toml`](../pyproject.toml) |
| Unique app name | `helios_order_visibility` is the declared app name; Marketplace uniqueness must be checked in the portal | [`helios_order_visibility/hooks.py`](../helios_order_visibility/hooks.py), [`marketplace/listing.json`](../marketplace/listing.json) |
| Current stable Frappe/ERPNext support | Declared range is documented; live validation remains a release gate | [`docs/compatibility.md`](compatibility.md), [`pyproject.toml`](../pyproject.toml), [`scripts/test-daytona.sh`](../scripts/test-daytona.sh) |
| Passing CI | GitHub Actions installs the test extra and runs pytest | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| Square logo at least 200×200 with no text | 256×256 text-free SVG | [`marketplace/logo.svg`](../marketplace/logo.svg), [`marketplace/listing.json`](../marketplace/listing.json) |
| Website, support, documentation, terms, privacy URLs | All five URLs are listed in the draft metadata; verify they resolve after the repository is public | [`marketplace/listing.json`](../marketplace/listing.json), [`docs/terms-of-service.md`](terms-of-service.md), [`docs/privacy-policy.md`](privacy-policy.md) |
| 40–80 character one-sentence summary | Draft summary is 68 characters and does not repeat the title | [`marketplace/listing.json`](../marketplace/listing.json) |
| Long description without install steps or repeated summary | Draft listing description contains features and usage only | [`marketplace/listing.json`](../marketplace/listing.json), [`marketplace/README.md`](../marketplace/README.md) |
| Screenshots/videos in listing media fields | No real UI captures exist yet; the listing intentionally has an empty array | [`marketplace/listing.json`](../marketplace/listing.json), [`proof/screenshots/README.md`](../proof/screenshots/README.md) |
| Release submitted in Marketplace Versions | Not done; requires a tagged release and portal action | [`marketplace/README.md`](../marketplace/README.md) |
| Security and authoring guidance | Uses hooks, does not override Frappe authentication routes, and has CI | [`helios_order_visibility/hooks.py`](../helios_order_visibility/hooks.py), [`docs/api.md`](api.md), [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |

The checklist distinguishes repository evidence from portal actions. Nothing in this repository says that the app is published, approved, certified, or live-tested when it is not.
