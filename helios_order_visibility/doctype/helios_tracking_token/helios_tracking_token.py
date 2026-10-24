from frappe.model.document import Document
import frappe


class HeliosTrackingToken(Document):
    def before_save(self):
        expires_at = frappe.utils.get_datetime(self.expires_at).replace(tzinfo=None) if self.expires_at else None
        now = frappe.utils.now_datetime().replace(tzinfo=None)
        if self.status == "Active" and expires_at and expires_at <= now:
            self.status = "Expired"
