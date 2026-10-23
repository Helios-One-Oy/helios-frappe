"""Real-bench tests. Run with `bench --site <site> run-tests --app helios_order_visibility`."""
import frappe
from frappe.tests.utils import FrappeTestCase


class TestSupplierConfirmation(FrappeTestCase):
    def setUp(self):
        self.company = frappe.get_all("Company", pluck="name", limit=1)[0]
        self.supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Northstar Precision (sample)", "supplier_group": "All Supplier Groups", "supplier_type": "Company"}).insert()
        self.item = frappe.get_doc({"doctype": "Item", "item_code": "SAMPLE-BRACKET", "item_name": "Sample bracket", "item_group": "All Item Groups", "stock_uom": "Nos", "is_stock_item": 1}).insert()
        self.po = frappe.get_doc({"doctype": "Purchase Order", "supplier": self.supplier.name, "company": self.company,
            "transaction_date": "2026-10-23", "items": [{"item_code": self.item.name, "qty": 2, "rate": 10, "schedule_date": "2026-10-30"}]}).insert()
        self.po.submit()

    def tearDown(self):
        for doctype, name in (("Purchase Order", self.po.name), ("Item", self.item.name), ("Supplier", self.supplier.name)):
            if frappe.db.exists(doctype, name):
                if doctype == "Purchase Order" and self.po.docstatus == 1:
                    self.po.cancel()
                frappe.delete_doc(doctype, name, force=True)

    def test_link_confirm_updates_po_and_line_schedule(self):
        from helios_order_visibility.services.supplier import ensure_confirmation, confirm_from_token
        from helios_order_visibility.services.tokens import decode_and_validate
        issued = ensure_confirmation(self.po)
        token = issued.get("link", "").rsplit("/", 1)[-1]
        # The raw token is not stored; issue a fresh test token for this assertion.
        from helios_order_visibility.services.tokens import issue_token
        raw, _ = issue_token("Purchase Order", self.po.name, "supplier_confirmation", frappe.utils.add_days(frappe.utils.now_datetime(), 2))
        result = confirm_from_token(raw, True, "2026-11-04", source="test")
        self.assertEqual(result["status"], "Confirmed")
        self.assertEqual(frappe.db.get_value("Purchase Order", self.po.name, "helios_supplier_schedule_date"), "2026-11-04")
        self.assertEqual(frappe.db.get_value("Purchase Order Item", self.po.items[0].name, "schedule_date"), "2026-11-04")

    def test_replayed_confirmation_is_idempotent(self):
        from helios_order_visibility.services.supplier import confirm_from_token
        from helios_order_visibility.services.tokens import issue_token
        raw, _ = issue_token("Purchase Order", self.po.name, "supplier_confirmation", frappe.utils.add_days(frappe.utils.now_datetime(), 2))
        first = confirm_from_token(raw, True, "2026-11-04", source="test")
        second = confirm_from_token(raw, True, "2026-11-04", source="test")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
