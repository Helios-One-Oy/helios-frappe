"""Human-readable supplier confirmation page used by the live proof."""
import frappe


def get_context(context):
    from helios_order_visibility.api import get_supplier_confirmation
    from helios_order_visibility.services.supplier import confirm_from_token

    token = frappe.form_dict.get("token")
    context.title = "Supplier PO confirmation"
    context.sample_label = "fictional sample data"
    context.error = None
    context.result = None
    if not token:
        context.error = "A signed supplier token is required."
        return context
    try:
        # The signed token is the capability for this guest form. Validate it
        # before disabling Frappe's normal CSRF check for the POST.
        from helios_order_visibility.services.tokens import decode_and_validate
        decode_and_validate(token, "supplier_confirmation")
        is_post = bool(frappe.local.request and str(frappe.local.request.method).upper() == "POST")
        # Some Frappe web adapters expose the form fields before the request
        # wrapper is populated; the signed token plus a submitted date is
        # still an unambiguous capability-form POST.
        is_post = is_post or bool(frappe.form_dict.get("schedule_date"))
        if is_post:
            frappe.local.no_csrf = True
        if is_post:
            confirmed = frappe.form_dict.get("confirmed", "true")
            context.result = confirm_from_token(
                token,
                str(confirmed).lower() in {"1", "true", "yes", "confirmed"},
                frappe.form_dict.get("schedule_date"),
                frappe.form_dict.get("note"),
                source="live-proof-page",
            )
        context.confirmation = get_supplier_confirmation(token)
    except Exception as exc:
        context.error = str(exc)
    return context
