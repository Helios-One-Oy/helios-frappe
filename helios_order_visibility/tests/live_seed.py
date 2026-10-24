"""Demo fixture: seed a clean ERPNext test site for the Daytona install run.

Every record created here is fictional demo data (example.com-style
addresses, invented company names). It is never loaded on a customer site;
only scripts/test-daytona.sh calls it. Dates are relative to the site's
today so the late/open split stays meaningful whenever the run happens.
"""
from __future__ import annotations

import json
import os

import frappe
from frappe.utils import add_days, nowdate


def _first(doctype: str, field: str, filters: dict | None = None):
    return frappe.db.get_value(doctype, filters or {}, field)


def run():
    # A non-UTC site time zone, so the run shows pages and stored datetimes
    # follow System Settings rather than the server clock.
    frappe.db.set_single_value("System Settings", "time_zone", "Europe/Helsinki")
    frappe.clear_cache()
    frappe.local.system_settings = None
    today = nowdate()
    on_time = add_days(today, 11)
    late = add_days(today, -23)
    confirm_date = add_days(today, 14)
    # Set the disposable test-site origin before any submitted document hooks run.
    # Those hooks persist the signed links on the PO/SO, so setting it after
    # submission would leave one of the two records pointing at helios.local.
    frappe.db.set_single_value("Helios Settings", "public_base_url", "http://127.0.0.1:8000")
    # A clean ERPNext install does not ship the standard warehouse types that
    # the Company on_update hook uses to create its defaults.
    for warehouse_type in ("Transit", "Stores", "Finished Goods", "Work In Progress"):
        if not frappe.db.exists("Warehouse Type", warehouse_type):
            frappe.get_doc({"doctype": "Warehouse Type", "name": warehouse_type}).insert(
                ignore_permissions=True
            )
    company = _first("Company", "name")
    if not company:
        doc = frappe.get_doc({
            "doctype": "Company", "company_name": "Example Manufacturing Oy",
            "abbr": "EXM", "default_currency": "USD", "country": "United States",
        }).insert(ignore_permissions=True)
        company = doc.name
    # ERPNext v16 does not create a Fiscal Year on a site without the setup
    # wizard; transactions need one covering their dates.
    from erpnext.accounts.utils import get_fiscal_year
    for year_date in {add_days(today, -45), add_days(today, 45)}:
        try:
            get_fiscal_year(year_date, company=company)
        except Exception:
            year = str(frappe.utils.getdate(year_date).year)
            frappe.get_doc({
                "doctype": "Fiscal Year", "year": year,
                "year_start_date": f"{year}-01-01", "year_end_date": f"{year}-12-31",
                "companies": [{"company": company}],
            }).insert(ignore_permissions=True)
    supplier_group = _first("Supplier Group", "name")
    if not supplier_group:
        doc = frappe.get_doc({
            "doctype": "Supplier Group", "supplier_group_name": "Demo Suppliers",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        supplier_group = doc.name
    customer_group = _first("Customer Group", "name")
    if not customer_group:
        doc = frappe.get_doc({
            "doctype": "Customer Group", "customer_group_name": "Demo Customers",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        customer_group = doc.name
    item_group = _first("Item Group", "name")
    if not item_group:
        doc = frappe.get_doc({
            "doctype": "Item Group", "item_group_name": "Demo Items",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        item_group = doc.name
    territory = _first("Territory", "name")
    if not territory:
        doc = frappe.get_doc({
            "doctype": "Territory", "territory_name": "Demo Territory",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        territory = doc.name
    uom = "Nos"
    if not frappe.db.exists("UOM", uom):
        frappe.get_doc({"doctype": "UOM", "uom_name": uom, "must_be_whole_number": 0}).insert(
            ignore_permissions=True
        )
    warehouse = _first("Warehouse", "name", {"company": company})
    if not warehouse:
        doc = frappe.get_doc({
            "doctype": "Warehouse", "warehouse_name": "Demo Warehouse",
            "company": company, "is_group": 0,
        }).insert(ignore_permissions=True)
        warehouse = doc.name

    supplier_name = "Example Supplier Ltd"
    if not frappe.db.exists("Supplier", supplier_name):
        frappe.get_doc({
            "doctype": "Supplier", "supplier_name": supplier_name,
            "supplier_group": supplier_group, "supplier_type": "Company",
            "email_id": "orders@supplier.example",
        }).insert(ignore_permissions=True)
    supplier = frappe.get_doc("Supplier", supplier_name)

    customer_name = "Example Customer Inc"
    if not frappe.db.exists("Customer", customer_name):
        frappe.get_doc({
            "doctype": "Customer", "customer_name": customer_name,
            "customer_group": customer_group, "territory": territory,
            "email_id": "buyer@customer.example",
        }).insert(ignore_permissions=True)

    item_code = "BRKT-6061-A"
    if not frappe.db.exists("Item", item_code):
        frappe.get_doc({
            "doctype": "Item", "item_code": item_code,
            "item_name": "Bracket blank, 6061 aluminium",
            "item_group": item_group, "stock_uom": uom, "is_stock_item": 0,
        }).insert(ignore_permissions=True)

    po_name = "PO-1042"
    if not frappe.db.exists("Purchase Order", po_name):
        po = frappe.get_doc({
            "doctype": "Purchase Order", "supplier": supplier.name,
            "company": company, "transaction_date": add_days(today, -30),
            "items": [{"item_code": item_code, "qty": 24, "rate": 100,
                        "schedule_date": on_time, "warehouse": warehouse}],
        }).insert(ignore_permissions=True)
        if po.name != po_name:
            frappe.rename_doc("Purchase Order", po.name, po_name, force=True)
            po = frappe.get_doc("Purchase Order", po_name)
        po.submit()
    po = frappe.get_doc("Purchase Order", po_name)

    late_po_name = "PO-1043"
    if not frappe.db.exists("Purchase Order", late_po_name):
        late_po = frappe.get_doc({
            "doctype": "Purchase Order", "supplier": supplier.name,
            "company": company, "transaction_date": add_days(today, -30),
            "items": [{"item_code": item_code, "qty": 8, "rate": 100,
                        "schedule_date": late, "warehouse": warehouse}],
        }).insert(ignore_permissions=True)
        if late_po.name != late_po_name:
            frappe.rename_doc("Purchase Order", late_po.name, late_po_name, force=True)
            late_po = frappe.get_doc("Purchase Order", late_po_name)
        late_po.submit()

    selling_price_list = _first("Price List", "name", {"selling": 1, "enabled": 1})
    if not selling_price_list:
        doc = frappe.get_doc({
            "doctype": "Price List", "price_list_name": "Demo Selling",
            "selling": 1, "buying": 0, "enabled": 1, "currency": "USD",
        }).insert(ignore_permissions=True)
        selling_price_list = doc.name
    price_list_currency = frappe.db.get_value("Price List", selling_price_list, "currency") or "USD"
    so_name = "SO-2007"
    if not frappe.db.exists("Sales Order", so_name):
        so = frappe.get_doc({
            "doctype": "Sales Order", "customer": customer_name,
            "company": company, "transaction_date": add_days(today, -3),
            "selling_price_list": selling_price_list,
            "price_list_currency": price_list_currency, "plc_conversion_rate": 1,
            "delivery_date": add_days(today, 21),
            "items": [{"item_code": item_code, "qty": 8, "rate": 100,
                        "delivery_date": add_days(today, 21), "warehouse": warehouse}],
        }).insert(ignore_permissions=True)
        if so.name != so_name:
            frappe.rename_doc("Sales Order", so.name, so_name, force=True)
            so = frappe.get_doc("Sales Order", so_name)
        so.submit()
    so = frappe.get_doc("Sales Order", so_name)

    # Ensure the hooks have materialised signed links, even if a site's submit
    # workflow was configured to skip application events.
    from helios_order_visibility.services.supplier import ensure_confirmation
    from helios_order_visibility.services.tracking import ensure_tracking_link
    from helios_order_visibility.services.tokens import revoke_token
    for token_name in frappe.get_all("Helios Tracking Token", filters={
        "reference_doctype": "Purchase Order", "reference_name": po.name,
        "purpose": "supplier_confirmation", "status": "Active"}, pluck="name"):
        revoke_token(token_name)
    frappe.db.set_value("Purchase Order", po.name, {
        "helios_confirmation_status": "Pending",
        "helios_supplier_confirmed_at": None,
        "helios_supplier_schedule_date": None,
        "helios_confirmation_source": None,
    }, update_modified=False)
    for item in frappe.get_all("Purchase Order Item", filters={"parent": po.name}, pluck="name"):
        frappe.db.set_value("Purchase Order Item", item, "schedule_date", on_time, update_modified=False)
    confirmation = ensure_confirmation(po)
    late_po = frappe.get_doc("Purchase Order", late_po_name)
    late_confirmation = ensure_confirmation(late_po)
    tracking = ensure_tracking_link(so, "Sales Order")
    # Re-read after the writes so returned links are usable by the browser run.
    po.reload(); so.reload()
    result = {
        "demo_data": "fictional demo fixture",
        "today": today, "today_display": frappe.utils.formatdate(today),
        "time_zone": frappe.utils.get_system_timezone(), "on_time_date": on_time, "late_date": late, "confirm_date": confirm_date,
        "company": company, "supplier": supplier.name, "customer": customer_name,
        "purchase_order": po.name, "sales_order": so.name,
        "supplier_token": confirmation.get("link", "").split("token=", 1)[-1],
        "customer_token": tracking.get("link", "").split("token=", 1)[-1],
        "late_token": (late_confirmation.get("link") or late_po.helios_confirmation_link or "").split("token=", 1)[-1],
        "supplier_url": po.helios_confirmation_link,
        "customer_url": so.helios_tracking_link,
        "supplier_status": po.helios_confirmation_status,
        "tracking_status": so.helios_tracking_status,
        "writeback": "pending_http_confirmation", "idempotent": "pending_http_replay",
    }
    proof_dir = os.environ.get("HELIOS_PROOF_DIR")
    if proof_dir:
        os.makedirs(proof_dir, exist_ok=True)
        # Keep capability tokens available only to the in-run browser. The
        # committed run metadata and console log retain routes and statuses
        # without publishing replayable guest credentials.
        runtime_result = dict(result)
        safe_result = dict(result)
        for key in ("supplier_token", "customer_token", "late_token"):
            safe_result[key] = "REDACTED_TOKEN"
        for key in ("supplier_url", "customer_url"):
            safe_result[key] = safe_result[key].split("?token=", 1)[0] + "?token=REDACTED_TOKEN"
        with open(os.path.join(proof_dir, "seed-runtime.json"), "w", encoding="utf-8") as fh:
            json.dump(runtime_result, fh, indent=2, default=str)
        with open(os.path.join(proof_dir, "seed-metadata.json"), "w", encoding="utf-8") as fh:
            json.dump(safe_result, fh, indent=2, default=str)
        return safe_result
    return result


def db_snapshot():
    """Print the persisted PO state after the browser run (writeback check)."""
    rows = frappe.db.sql("""
        select po.name as purchase_order, po.helios_confirmation_status, po.helios_supplier_schedule_date,
               po.helios_supplier_confirmed_at, po.helios_confirmation_source, poi.item_code, poi.schedule_date
        from `tabPurchase Order` po join `tabPurchase Order Item` poi on poi.parent = po.name
        where po.name in ('PO-1042', 'PO-1043') order by po.name
    """, as_dict=True)
    audit = frappe.get_all("Supplier PO Confirmation", fields=["purchase_order", "status", "schedule_date", "confirmation_source", "confirmed_at", "note"])
    tokens = frappe.get_all("Helios Tracking Token", fields=["reference_name", "purpose", "status", "expires_at"])
    result = {"time_zone": frappe.utils.get_system_timezone(), "site_now": str(frappe.utils.now_datetime()), "purchase_orders": rows, "audit": audit, "tokens": tokens}
    print(json.dumps(result, indent=2, default=str))
    return result
