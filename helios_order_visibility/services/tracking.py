from __future__ import annotations

from datetime import timedelta

from .common import field, now_utc, public_base_url
from .tokens import TOKEN_DOCTYPE, decode_and_validate, issue_token, revoke_token


def _frappe():
    import frappe
    return frappe


def _expiry_days():
    frappe = _frappe()
    try:
        value = frappe.db.get_single_value("Helios Settings", "customer_link_expiry_days")
        return max(1, min(int(value or 90), 365))
    except Exception:
        return 90


def _active(reference_doctype, reference_name):
    frappe = _frappe()
    rows = frappe.get_all(TOKEN_DOCTYPE, filters={"reference_doctype": reference_doctype, "reference_name": reference_name, "purpose": "customer_tracking", "status": "Active"}, fields=["name", "expires_at"])
    return rows[0] if rows else None


def ensure_tracking_link(doc, doctype):
    frappe = _frappe()
    name = field(doc, "name")
    existing = _active(doctype, name)
    if existing:
        return {**existing, "link": field(doc, "helios_tracking_link")}
    expires = now_utc() + timedelta(days=_expiry_days())
    customer_email = field(doc, "contact_email") or field(doc, "customer_email") or ""
    raw, jti = issue_token(doctype, name, "customer_tracking", expires, {"customer_email": customer_email})
    base = public_base_url(frappe)
    link = f"{base}/helios/track/{raw}"
    for key, value in {"helios_tracking_status": "Active", "helios_tracking_link": link}.items():
        if hasattr(doc, "db_set"):
            doc.db_set(key, value, update_modified=False)
        else:
            frappe.db.set_value(doctype, name, key, value, update_modified=False)
    return {"name": jti, "expires_at": expires.isoformat(), "link": link}


def revoke_tracking_link(doctype, name):
    frappe = _frappe()
    for token_name in frappe.get_all(TOKEN_DOCTYPE, filters={"reference_doctype": doctype, "reference_name": name, "purpose": "customer_tracking", "status": "Active"}, pluck="name"):
        revoke_token(token_name)
    frappe.db.set_value(doctype, name, "helios_tracking_status", "Revoked", update_modified=True)


def _safe_items(doctype, name):
    frappe = _frappe()
    item_doctype = "Sales Order Item" if doctype == "Sales Order" else "Delivery Note Item"
    fields = ["item_code", "item_name", "qty", "uom"]
    if doctype == "Sales Order":
        fields += ["schedule_date", "delivered_qty"]
    rows = frappe.get_all(item_doctype, filters={"parent": name}, fields=fields)
    return [{k: row.get(k) for k in ("item_code", "item_name", "qty", "uom", "schedule_date", "delivered_qty") if row.get(k) is not None} for row in rows]


def tracking_snapshot(raw_token):
    claims = decode_and_validate(raw_token, "customer_tracking")
    frappe = _frappe()
    doctype, name = claims["doctype"], claims["name"]
    if doctype not in {"Sales Order", "Delivery Note"}:
        raise ValueError("unsupported tracking reference")
    doc = frappe.get_doc(doctype, name)
    snapshot = {"reference_doctype": doctype, "reference_name": name, "status": field(doc, "status"), "transaction_date": str(field(doc, "transaction_date") or ""), "customer": field(doc, "customer_name") or field(doc, "customer"), "items": _safe_items(doctype, name)}
    if doctype == "Sales Order":
        snapshot.update({"delivery_date": str(field(doc, "delivery_date") or ""), "per_delivered": field(doc, "per_delivered"), "delivery_notes": frappe.get_all("Delivery Note Item", filters={"against_sales_order": name}, fields=["parent", "qty"])})
    else:
        snapshot.update({"posting_date": str(field(doc, "posting_date") or ""), "sales_order": field(doc, "against_sales_order")})
    return snapshot


def tracking_link_for(doctype, name):
    """Return the existing link without exposing the token record to guests."""
    frappe = _frappe()
    row = frappe.get_all(TOKEN_DOCTYPE, filters={"reference_doctype": doctype,
        "reference_name": name, "purpose": "customer_tracking", "status": "Active"},
        fields=["name", "expires_at"], limit=1)
    return row[0] if row else None
