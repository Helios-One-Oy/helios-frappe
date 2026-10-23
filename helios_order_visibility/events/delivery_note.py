def on_submit(doc, method=None):
    from helios_order_visibility.services.tracking import ensure_tracking_link
    ensure_tracking_link(doc, "Delivery Note")


def on_cancel(doc, method=None):
    from helios_order_visibility.services.tracking import revoke_tracking_link
    revoke_tracking_link("Delivery Note", doc.name)
