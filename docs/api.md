# API surface

The following endpoints are intentionally small:

| Endpoint | Auth | Purpose |
| --- | --- | --- |
| `GET /api/method/helios_order_visibility.api.get_supplier_confirmation` | signed guest token | Read supplier PO name, supplier, status, and expiry |
| `POST /api/method/helios_order_visibility.api.confirm_supplier_purchase_order` | signed guest token | Confirm/reject and write an optional schedule date |
| `GET /api/method/helios_order_visibility.api.get_customer_order_tracking` | signed guest token | Read the filtered Sales Order/Delivery Note snapshot |
| `POST /api/method/helios_order_visibility.api.parse_supplier_confirmation_email` | authenticated write user | Run the constrained email parser manually |

The website routes `/helios/confirm/<token>` and `/helios/track/<token>` call those same services. There is no override of `/login`, `/update`, or any standard Frappe authentication route. Signed tokens are HMAC-SHA256 over a versioned payload and are bound in the database to one purpose and reference record.
