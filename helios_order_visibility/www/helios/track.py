"""Human-readable customer tracking page used by the live proof."""
import frappe


def get_context(context):
    from helios_order_visibility.services.tracking import tracking_snapshot

    token = frappe.form_dict.get("token")
    context.title = "Customer order tracking"
    context.sample_label = "fictional sample data"
    context.error = None
    context.snapshot = None
    if not token:
        context.error = "A signed customer token is required."
        return context
    try:
        context.snapshot = tracking_snapshot(token)
    except Exception as exc:
        context.error = str(exc)
    return context
