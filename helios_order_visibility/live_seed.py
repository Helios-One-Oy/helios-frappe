"""Seed and exercise a small fictional ERPNext site for the Daytona proof."""
from __future__ import annotations

import json
import os

import frappe


def _first(doctype: str, field: str, filters: dict | None = None):
    return frappe.db.get_value(doctype, filters or {}, field)


def run():
    # Set the disposable proof origin before any submitted document hooks run.
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
            "doctype": "Company", "company_name": "M3 Fictional Manufacturing Oy",
            "abbr": "M3F", "default_currency": "USD", "country": "United States",
        }).insert(ignore_permissions=True)
        company = doc.name
    supplier_group = _first("Supplier Group", "name")
    if not supplier_group:
        doc = frappe.get_doc({
            "doctype": "Supplier Group", "supplier_group_name": "M3 Fictional Suppliers",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        supplier_group = doc.name
    customer_group = _first("Customer Group", "name")
    if not customer_group:
        doc = frappe.get_doc({
            "doctype": "Customer Group", "customer_group_name": "M3 Fictional Customers",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        customer_group = doc.name
    item_group = _first("Item Group", "name")
    if not item_group:
        doc = frappe.get_doc({
            "doctype": "Item Group", "item_group_name": "M3 Fictional Items",
            "is_group": 0,
        }).insert(ignore_permissions=True)
        item_group = doc.name
    territory = _first("Territory", "name")
    if not territory:
        doc = frappe.get_doc({
            "doctype": "Territory", "territory_name": "M3 Fictional Territory",
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
            "doctype": "Warehouse", "warehouse_name": "M3 Fictional Warehouse",
            "company": company, "is_group": 0,
        }).insert(ignore_permissions=True)
        warehouse = doc.name

    supplier_name = "Northstar Precision (fictional)"
    if not frappe.db.exists("Supplier", supplier_name):
        frappe.get_doc({
            "doctype": "Supplier", "supplier_name": supplier_name,
            "supplier_group": supplier_group, "supplier_type": "Company",
            "email_id": "buyer@northstar.example",
        }).insert(ignore_permissions=True)
    supplier = frappe.get_doc("Supplier", supplier_name)

    customer_name = "Acme Robotics (fictional)"
    if not frappe.db.exists("Customer", customer_name):
        frappe.get_doc({
            "doctype": "Customer", "customer_name": customer_name,
            "customer_group": customer_group, "territory": territory,
            "email_id": "ops@acme-robotics.example",
        }).insert(ignore_permissions=True)

    item_code = "M3-SAMPLE-BRACKET"
    if not frappe.db.exists("Item", item_code):
        frappe.get_doc({
            "doctype": "Item", "item_code": item_code,
            "item_name": "Sample bracket blank (fictional)",
            "item_group": item_group, "stock_uom": uom, "is_stock_item": 0,
        }).insert(ignore_permissions=True)

    po_name = "M3-SUP-0042"
    if not frappe.db.exists("Purchase Order", po_name):
        po = frappe.get_doc({
            "doctype": "Purchase Order", "supplier": supplier.name,
            "company": company, "transaction_date": "2026-09-20",
            "items": [{"item_code": item_code, "qty": 24, "rate": 100,
                        "schedule_date": "2026-11-04", "warehouse": warehouse}],
        }).insert(ignore_permissions=True)
        if po.name != po_name:
            frappe.rename_doc("Purchase Order", po.name, po_name, force=True)
            po = frappe.get_doc("Purchase Order", po_name)
        po.submit()
    po = frappe.get_doc("Purchase Order", po_name)

    late_po_name = "M3-SUP-0043"
    if not frappe.db.exists("Purchase Order", late_po_name):
        late_po = frappe.get_doc({
            "doctype": "Purchase Order", "supplier": supplier.name,
            "company": company, "transaction_date": "2026-09-20",
            "items": [{"item_code": item_code, "qty": 8, "rate": 100,
                        "schedule_date": "2026-10-01", "warehouse": warehouse}],
        }).insert(ignore_permissions=True)
        if late_po.name != late_po_name:
            frappe.rename_doc("Purchase Order", late_po.name, late_po_name, force=True)
            late_po = frappe.get_doc("Purchase Order", late_po_name)
        late_po.submit()

    selling_price_list = _first("Price List", "name", {"selling": 1, "enabled": 1})
    if not selling_price_list:
        doc = frappe.get_doc({
            "doctype": "Price List", "price_list_name": "M3 Fictional Selling",
            "selling": 1, "buying": 0, "enabled": 1, "currency": "USD",
        }).insert(ignore_permissions=True)
        selling_price_list = doc.name
    price_list_currency = frappe.db.get_value("Price List", selling_price_list, "currency") or "USD"
    so_name = "M3-CUS-0007"
    if not frappe.db.exists("Sales Order", so_name):
        so = frappe.get_doc({
            "doctype": "Sales Order", "customer": customer_name,
            "company": company, "transaction_date": "2026-10-21",
            "selling_price_list": selling_price_list,
            "price_list_currency": price_list_currency, "plc_conversion_rate": 1,
            "delivery_date": "2026-11-14",
            "items": [{"item_code": item_code, "qty": 8, "rate": 100,
                        "delivery_date": "2026-11-14", "warehouse": warehouse}],
        }).insert(ignore_permissions=True)
        if so.name != so_name:
            frappe.rename_doc("Sales Order", so.name, so_name, force=True)
            so = frappe.get_doc("Sales Order", so_name)
        so.submit()
    so = frappe.get_doc("Sales Order", so_name)

    # Ensure the hooks have materialised signed links, even if a site's submit
    # workflow was configured to skip application events.
    from .services.supplier import ensure_confirmation
    from .services.tracking import ensure_tracking_link
    from .services.tokens import revoke_token
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
        frappe.db.set_value("Purchase Order Item", item, "schedule_date", "2026-11-04", update_modified=False)
    confirmation = ensure_confirmation(po)
    tracking = ensure_tracking_link(so, "Sales Order")
    # Re-read after the writes so returned links are usable by the HTTP proof.
    po.reload(); so.reload()
    result = {
        "sample_label": "fictional sample data",
        "company": company, "supplier": supplier.name, "customer": customer_name,
        "purchase_order": po.name, "sales_order": so.name,
        "supplier_token": confirmation.get("link", "").split("token=", 1)[-1],
        "customer_token": tracking.get("link", "").split("token=", 1)[-1],
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
        # committed proof metadata and console log retain routes and statuses
        # without publishing replayable guest credentials.
        runtime_result = dict(result)
        safe_result = dict(result)
        for key in ("supplier_token", "customer_token"):
            safe_result[key] = "REDACTED_TOKEN"
        for key in ("supplier_url", "customer_url"):
            safe_result[key] = safe_result[key].split("?token=", 1)[0] + "?token=REDACTED_TOKEN"
        with open(os.path.join(proof_dir, "seed-runtime.json"), "w", encoding="utf-8") as fh:
            json.dump(runtime_result, fh, indent=2, default=str)
        with open(os.path.join(proof_dir, "seed-metadata.json"), "w", encoding="utf-8") as fh:
            json.dump(safe_result, fh, indent=2, default=str)
        return safe_result
    return result
