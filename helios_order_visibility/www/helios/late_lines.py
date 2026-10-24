"""Authenticated late supplier-line review page."""
import frappe


def get_context(context):
    from helios_order_visibility.report.supplier_otd.supplier_otd import execute

    if frappe.session.user in (None, "Guest"):
        frappe.throw("Login is required to view supplier delivery data", frappe.PermissionError)
    context.title = "Late supplier lines"
    context.sample_label = "fictional sample data"
    context.error = None
    context.rows = []
    try:
        _columns, rows = execute({"otd_status": "Late open"})
        context.rows = rows
    except Exception as exc:
        context.error = str(exc)
    return context
