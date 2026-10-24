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
        if frappe.local.request and frappe.local.request.method == "POST":
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
