"""Guest and report pages must escape ERPNext values.

Frappe renders website pages in a Jinja SandboxedEnvironment without
autoescape, so the templates turn it on themselves. This renders them the
same way with hostile record values.
"""
from pathlib import Path
from types import SimpleNamespace

from jinja2.sandbox import SandboxedEnvironment

WWW = Path(__file__).resolve().parents[1] / "helios_order_visibility" / "www" / "helios"
EVIL = '<script>alert(1)</script>"><img src=x onerror=alert(2)>'


def render(name, **context):
    env = SandboxedEnvironment()  # like Frappe: autoescape off
    base = {
        "frappe": SimpleNamespace(session=SimpleNamespace(user=EVIL)),
        "company": EVIL, "today": EVIL, "title": EVIL, "error": None,
        "token": EVIL, "csrf_token": EVIL,
    }
    base.update(context)
    return env.from_string((WWW / f"{name}.html").read_text()).render(**base)


def assert_escaped(html):
    assert "<script>" not in html and "<img src=x" not in html
    assert "&lt;script&gt;" in html


def test_supplier_confirmation_escapes_record_values():
    item = {"item_code": EVIL, "item_name": EVIL, "qty_display": EVIL, "uom": EVIL, "schedule_display": EVIL}
    confirmation = {"purchase_order": EVIL, "company": EVIL, "supplier": EVIL, "status": "Pending",
                    "requested_display": EVIL, "schedule_display": EVIL, "expires_display": EVIL,
                    "form_date": EVIL, "items": [item]}
    assert_escaped(render("confirm", confirmation=confirmation, result=None))
    assert_escaped(render("confirm", confirmation=None, result=None, error=EVIL))


def test_customer_tracking_escapes_record_values():
    item = {"item_code": EVIL, "item_name": EVIL, "qty_display": EVIL, "uom": EVIL,
            "delivered_display": EVIL, "schedule_display": EVIL}
    snapshot = {"reference_doctype": "Sales Order", "reference_name": EVIL, "company": EVIL, "customer": EVIL,
                "status": EVIL, "transaction_date_display": EVIL, "delivery_date_display": EVIL,
                "posting_date_display": EVIL, "sales_order": EVIL, "items": [item],
                "delivery_notes": [{"parent": EVIL, "qty": EVIL}]}
    assert_escaped(render("track", snapshot=snapshot))


def test_report_pages_escape_record_values():
    row = {"purchase_order": EVIL, "supplier": EVIL, "item_code": EVIL, "schedule_display": EVIL,
           "received_display": EVIL, "days_late": EVIL, "otd_status": EVIL, "qty_display": EVIL}
    assert_escaped(render("otd", rows=[row]))
    assert_escaped(render("late_lines", rows=[row]))
