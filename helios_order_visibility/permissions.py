def has_permission(doc, ptype="read", user=None):
    """Only internal users with an app role can read/write token records."""
    import frappe
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    roles = set(frappe.get_roles(user))
    return bool(roles.intersection({"Helios Order Visibility Manager", "Helios Order Visibility User"}))
