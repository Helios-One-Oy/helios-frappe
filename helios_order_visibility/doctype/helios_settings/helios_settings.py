import frappe
from frappe.model.document import Document


class HeliosSettings(Document):
    def validate(self):
        if self.supplier_link_expiry_days < 1 or self.supplier_link_expiry_days > 90:
            frappe.throw("Supplier link expiry must be between 1 and 90 days")
        if self.customer_link_expiry_days < 1 or self.customer_link_expiry_days > 365:
            frappe.throw("Customer link expiry must be between 1 and 365 days")
