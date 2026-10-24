"""Customer order status page behind a signed Sales Order or Delivery Note link."""
import frappe

# Each signed link renders different data; never serve this page from the
# website cache, which is keyed by path only.
no_cache = 1
sitemap = 0


def get_context(context):
    from helios_order_visibility.services.common import company_display_name, display_date, display_qty, site_today
    from helios_order_visibility.services.tracking import tracking_snapshot

    context.no_cache = 1
    token = frappe.form_dict.get("token")
    context.title = "Order status"
    context.error = None
    context.snapshot = None
    context.company = company_display_name(frappe)
    context.today = display_date(frappe, site_today(frappe))
    if not token:
        context.error = "This page needs the tracking link from your order email."
        return context
    try:
        snapshot = tracking_snapshot(token)
        context.company = snapshot["company"] or context.company
        context.title = f"Order {snapshot['reference_name']}"
        for key in ("transaction_date", "delivery_date", "posting_date"):
            snapshot[key + "_display"] = display_date(frappe, snapshot.get(key))
        for item in snapshot["items"]:
            item["schedule_display"] = display_date(frappe, item.get("schedule_date"))
            item["qty_display"] = display_qty(item.get("qty"))
            item["delivered_display"] = display_qty(item.get("delivered_qty") or 0)
        context.snapshot = snapshot
    except Exception as exc:
        context.error = str(exc)
    return context
