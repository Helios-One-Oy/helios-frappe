# Operations

After installation, assign **Helios Order Visibility Manager** to purchasing or implementation administrators and **Helios Order Visibility User** to users who need the report and token list. Guest visitors can use only a valid link; they never receive Frappe session access or token-record fields.

The PO submit hook creates one active supplier capability link. The link expires using **Helios Settings → Supplier Link Expiry (Days)**. A supplier can confirm or reject and provide an ISO date such as `2026-11-04`. The same date is written to the PO custom field and each open PO item `schedule_date`. A matching supplier email reply such as `Re: PO-SAMPLE-0042` with `Confirmed. ETA: 2026-11-04` follows the same state transition. Sender address and optional `Message-ID` replay checks are required. Unknown or malformed messages remain in Communication for review.

Sales Order and Delivery Note submit hooks create customer tracking links. The guest snapshot contains only customer-facing status, dates, line quantities, and delivery references; it excludes prices, addresses, internal notes, and token hashes. Cancelled documents can be handled by revoking their token through the authenticated app service before sending a replacement.

The daily scheduler marks expired token records and their app-owned status fields as **Expired**. Changing the encryption key invalidates all existing links by design. Never copy raw tokens into logs or support tickets. Rotate links by revoking the token record and submitting a new document event or calling the authenticated service.

## Upgrade safety

`after_migrate` creates the two app roles and only missing custom fields. It does not alter existing field definitions or ERPNext core tables. The app-owned DocTypes are standard JSON fixtures and are synced by Frappe. If a migration is interrupted, rerun `bench --site <site> migrate`; all setup is idempotent.
