"""Authenticated supplier on-time-delivery page."""
import frappe

no_cache = 1
sitemap = 0


def get_context(context):
    from helios_order_visibility.report.supplier_otd.supplier_otd import execute
    from helios_order_visibility.services.common import company_display_name, display_date, site_today

    context.no_cache = 1
    if frappe.session.user in (None, "Guest"):
        frappe.throw("Login is required to view supplier delivery data", frappe.PermissionError)
    context.title = "Supplier on-time delivery"
    context.company = company_display_name(frappe)
    context.today = display_date(frappe, site_today(frappe))
    context.error = None
    context.rows = []
    try:
        _columns, rows = execute({"supplier": frappe.form_dict.get("supplier")})
        for row in rows:
            row["schedule_display"] = display_date(frappe, row.get("schedule_date"))
            row["received_display"] = display_date(frappe, row.get("received_date"))
        context.rows = rows
    except Exception as exc:
        context.error = str(exc)
    return context
