from frappe.model.document import Document
import frappe


class HeliosTrackingToken(Document):
    def before_save(self):
        if self.status == "Active" and self.expires_at and self.expires_at <= frappe.utils.now_datetime():
            self.status = "Expired"
