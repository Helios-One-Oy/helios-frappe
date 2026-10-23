def on_submit(doc, method=None):
    from helios_order_visibility.services.supplier import ensure_confirmation
    ensure_confirmation(doc)


def on_cancel(doc, method=None):
    from helios_order_visibility.services.supplier import revoke_confirmation
    revoke_confirmation(doc)
