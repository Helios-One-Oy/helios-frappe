"""Small guest API surface for links and authenticated email/report methods."""
from __future__ import annotations

import frappe

from .services.supplier import confirm_from_token, process_incoming_email, supplier_confirmation_view
from .services.tracking import tracking_snapshot


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_supplier_confirmation(token):
    return supplier_confirmation_view(token)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def confirm_supplier_purchase_order(token, confirmed=True, schedule_date=None, note=None):
    # Notes are deliberately not written into the PO: callers can use the normal
    # Frappe comment API if an auditable free-text note is required.
    if isinstance(confirmed, str):
        confirmed = confirmed.lower() in {"1", "true", "yes", "confirmed"}
    # Frappe's guest POST normally expects a CSRF token. A signed, expiring
    # supplier token is the capability for this endpoint, so the website route
    # marks the request as no-CSRF only after the token has been validated.
    return confirm_from_token(token, bool(confirmed), schedule_date, note, source="link")


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_customer_order_tracking(token):
    return tracking_snapshot(token)


@frappe.whitelist(methods=["POST"])
def parse_supplier_confirmation_email(sender, subject, body, message_id=None):
    if not frappe.has_permission("Purchase Order", "write"):
        frappe.throw("Purchase Order write permission is required")
    return process_incoming_email(sender, subject, body, message_id)
