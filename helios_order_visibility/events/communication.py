def after_insert(doc, method=None):
    import frappe
    if (getattr(doc, "communication_type", "") or "").lower() != "communication":
        return
    if not getattr(doc, "sender", None) or not (getattr(doc, "subject", None) or getattr(doc, "content", None)):
        return
    from helios_order_visibility.services.supplier import process_incoming_email
    try:
        process_incoming_email(doc.sender, doc.subject or "", doc.content or "", getattr(doc, "message_id", None))
    except (PermissionError, ValueError):
        # Untrusted/malformed mail stays visible in Communication for review.
        frappe.log_error(frappe.get_traceback(), "Helios supplier reply parser")
