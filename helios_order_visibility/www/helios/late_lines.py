"""Authenticated late supplier-line page."""
import frappe

no_cache = 1
sitemap = 0


def get_context(context):
    from helios_order_visibility.report.supplier_otd.supplier_otd import execute
    from helios_order_visibility.services.common import company_display_name, display_date, display_qty, site_today

    context.no_cache = 1
    if frappe.session.user in (None, "Guest"):
        frappe.throw("Login is required to view supplier delivery data", frappe.PermissionError)
    context.title = "Late supplier lines"
    context.company = company_display_name(frappe)
    context.today = display_date(frappe, site_today(frappe))
    context.error = None
    context.rows = []
    try:
        _columns, rows = execute({"otd_status": "Late open"})
        for row in rows:
            row["schedule_display"] = display_date(frappe, row.get("schedule_date"))
            row["qty_display"] = display_qty(row.get("qty"))
        context.rows = rows
    except Exception as exc:
        context.error = str(exc)
    return context
