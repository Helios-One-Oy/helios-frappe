"""Supplier confirmation page behind a signed Purchase Order link."""
import frappe

# Each signed link renders different data; never serve this page from the
# website cache, which is keyed by path only.
no_cache = 1
sitemap = 0


def get_context(context):
    from helios_order_visibility.services.common import company_display_name, display_date, display_qty, site_today
    from helios_order_visibility.services.supplier import confirm_from_token, supplier_confirmation_view
    from helios_order_visibility.services.tokens import decode_and_validate

    context.no_cache = 1
    token = frappe.form_dict.get("token")
    context.title = "Confirm purchase order"
    context.error = None
    context.result = None
    context.confirmation = None
    context.token = token
    # Signed-in desk users (a buyer checking the link) need Frappe's CSRF token
    # on the POST; guests have none, the signed link is their capability.
    context.csrf_token = frappe.sessions.get_csrf_token() if frappe.session.user != "Guest" else ""
    context.company = company_display_name(frappe)
    context.today = display_date(frappe, site_today(frappe))
    if not token:
        context.error = "This page needs the confirmation link from your purchase order email."
        return context
    try:
        # The signed token is the capability for this guest form; validate it
        # before handling a POST.
        decode_and_validate(token, "supplier_confirmation")
        if frappe.local.request and str(frappe.local.request.method).upper() == "POST":
            confirmed = frappe.form_dict.get("confirmed", "true")
            context.result = confirm_from_token(
                token,
                str(confirmed).lower() in {"1", "true", "yes", "confirmed"},
                frappe.form_dict.get("schedule_date"),
                frappe.form_dict.get("note"),
                source="link",
            )
        view = supplier_confirmation_view(token)
        context.company = view["company"] or context.company
        context.title = f"Confirm {view['purchase_order']}"
        view["requested_display"] = display_date(frappe, view["requested_date"])
        view["schedule_display"] = display_date(frappe, view["schedule_date"])
        view["expires_display"] = display_date(frappe, view["expires_on"])
        view["form_date"] = str(view["schedule_date"] or view["requested_date"] or "")[:10]
        for item in view["items"]:
            item["schedule_display"] = display_date(frappe, item["schedule_date"])
            item["qty_display"] = display_qty(item["qty"])
        context.confirmation = view
    except Exception as exc:
        context.error = str(exc)
    return context
