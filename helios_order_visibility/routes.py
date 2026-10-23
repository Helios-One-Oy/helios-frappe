def confirm(token):
    """Website route for a supplier link (GET renders data; POST confirms)."""
    import frappe
    from .services.tokens import decode_and_validate
    from .api import get_supplier_confirmation, confirm_supplier_purchase_order
    decode_and_validate(token, "supplier_confirmation")
    if frappe.local.request and frappe.local.request.method == "POST":
        # The capability token was checked above; Frappe guest routes can now
        # safely accept the small form payload without a login session.
        frappe.local.no_csrf = True
        return confirm_supplier_purchase_order(token, frappe.form_dict.get("confirmed", True),
            frappe.form_dict.get("schedule_date"), frappe.form_dict.get("note"))
    return get_supplier_confirmation(token)


def track(token):
    from .api import get_customer_order_tracking
    return get_customer_order_tracking(token)
