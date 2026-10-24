app_name = "helios_order_visibility"
app_title = "Helios Order Visibility"
app_publisher = "Helios One Oy"
app_description = "Signed supplier confirmations and customer order tracking for ERPNext"
app_email = "support@heliosone.fi"
app_license = "MIT"
app_version = "0.1.0"

required_apps = ["erpnext"]

# Frappe syncs these records during install/update; the patch also creates them
# safely on sites that already contain older customisations.
fixtures = [
    {"dt": "Custom Field", "filters": [["name", "like", "Purchase Order-helios_%"]]},
    {"dt": "Custom Field", "filters": [["name", "like", "Sales Order-helios_%"]]},
    {"dt": "Custom Field", "filters": [["name", "like", "Delivery Note-helios_%"]]},
    {"dt": "Role", "filters": [["role_name", "in", ["Helios Order Visibility Manager", "Helios Order Visibility User"]]]},
]

doc_events = {
    "Purchase Order": {
        "on_submit": "helios_order_visibility.events.purchase_order.on_submit",
        "on_cancel": "helios_order_visibility.events.purchase_order.on_cancel",
    },
    "Sales Order": {
        "on_submit": "helios_order_visibility.events.sales_order.on_submit",
        "on_cancel": "helios_order_visibility.events.sales_order.on_cancel",
    },
    "Delivery Note": {
        "on_submit": "helios_order_visibility.events.delivery_note.on_submit",
        "on_cancel": "helios_order_visibility.events.delivery_note.on_cancel",
    },
    "Communication": {"after_insert": "helios_order_visibility.events.communication.after_insert"},
}

scheduler_events = {"daily": ["helios_order_visibility.tasks.expire_tokens"]}

after_migrate = "helios_order_visibility.patches.v1_0.ensure_custom_fields"

# Keep public endpoints narrow. No standard Frappe authentication endpoints are overridden.
website_route_rules = [
    {"from_route": "/helios/confirm/<token>", "to_route": "helios_order_visibility.routes.confirm"},
    {"from_route": "/helios/track/<token>", "to_route": "helios_order_visibility.routes.track"},
]

# Hook-based permission checks protect app-owned records and report data.
has_permission = {"Helios Tracking Token": "helios_order_visibility.permissions.has_permission"}

user_data_fields = [
    {"doctype": "Helios Tracking Token", "filter_by": "customer_email", "redact_fields": ["customer_email"]},
    {"doctype": "Supplier PO Confirmation", "filter_by": "supplier_email", "redact_fields": ["supplier_email"]},
]
