"""Migration-safe setup for existing ERPNext sites."""

CUSTOM_FIELDS = {
    "Purchase Order": [
        {"fieldname": "helios_confirmation_status", "label": "Supplier Confirmation Status", "fieldtype": "Select", "options": "Pending\nConfirmed\nRejected\nExpired\nRevoked", "insert_after": "status", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "helios_supplier_confirmed_at", "label": "Supplier Confirmed At", "fieldtype": "Datetime", "insert_after": "helios_confirmation_status", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "helios_supplier_schedule_date", "label": "Supplier Schedule Date", "fieldtype": "Date", "insert_after": "helios_supplier_confirmed_at", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "helios_confirmation_source", "label": "Confirmation Source", "fieldtype": "Data", "insert_after": "helios_supplier_schedule_date", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "helios_confirmation_message_id", "label": "Confirmation Message ID", "fieldtype": "Data", "insert_after": "helios_confirmation_source", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "helios_confirmation_link", "label": "Supplier Confirmation Link", "fieldtype": "Data", "insert_after": "helios_supplier_schedule_date", "read_only": 1, "allow_on_submit": 1},
    ],
    "Sales Order": [
        {"fieldname": "helios_tracking_status", "label": "Customer Tracking Status", "fieldtype": "Select", "options": "Active\nExpired\nRevoked", "insert_after": "status", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "helios_tracking_link", "label": "Customer Tracking Link", "fieldtype": "Data", "insert_after": "helios_tracking_status", "read_only": 1, "allow_on_submit": 1},
    ],
    "Delivery Note": [
        {"fieldname": "helios_tracking_status", "label": "Customer Tracking Status", "fieldtype": "Select", "options": "Active\nExpired\nRevoked", "insert_after": "status", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "helios_tracking_link", "label": "Customer Tracking Link", "fieldtype": "Data", "insert_after": "helios_tracking_status", "read_only": 1, "allow_on_submit": 1},
    ],
}

ROLES = ("Helios Order Visibility Manager", "Helios Order Visibility User")


def ensure_custom_fields():
    import frappe
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
    for doctype, definitions in CUSTOM_FIELDS.items():
        for definition in definitions:
            name = f"{doctype}-{definition['fieldname']}"
            if frappe.db.exists("Custom Field", name):
                continue
            frappe.get_doc({"doctype": "Custom Field", "name": name, "dt": doctype, **definition}).insert(ignore_permissions=True)
