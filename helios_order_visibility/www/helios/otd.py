"""Simple guest review page for the supplier OTD script report."""
import frappe


def get_context(context):
    from helios_order_visibility.report.supplier_otd.supplier_otd import execute

    context.title = "Supplier OTD"
    context.sample_label = "fictional sample data"
    context.error = None
    context.rows = []
    try:
        _columns, context.rows = execute({"supplier": frappe.form_dict.get("supplier")})
    except Exception as exc:
        context.error = str(exc)
    return context
