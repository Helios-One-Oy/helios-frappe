"""End-to-end service paths with a deterministic, in-memory Frappe adapter.

This is deliberately smaller than a Bench but exercises the same service
boundaries used by hooks and guest endpoints: issue, confirm, email replay,
and customer tracking.
"""

from datetime import datetime, timedelta, timezone
import sys
import types

import pytest

from helios_order_visibility.services.supplier import (
    confirm_from_token,
    ensure_confirmation,
    process_incoming_email,
)
from helios_order_visibility.services.tokens import issue_token
from helios_order_visibility.services.tracking import ensure_tracking_link, tracking_snapshot


class MemoryDB:
    def __init__(self):
        self.rows = {}
        self.settings = {"supplier_link_expiry_days": 7, "customer_link_expiry_days": 30, "public_base_url": "https://erp.example.test"}

    def get_single_value(self, doctype, field):
        return self.settings.get(field)

    def exists(self, doctype, name):
        return (doctype, name) in self.rows

    def get_value(self, doctype, name, fields, as_dict=False):
        if isinstance(name, dict):
            name = next((key[1] for key in self.rows if key[0] == doctype), None)
        row = self.rows.get((doctype, name))
        if row is None:
            return None
        if isinstance(fields, (list, tuple)):
            value = {key: row.get(key) for key in fields}
            return value if as_dict else value.get(fields[0])
        return row.get(fields)

    def set_value(self, doctype, name, field, value, **kwargs):
        row = self.rows.setdefault((doctype, name), {})
        row[field] = value


class Doc:
    def __init__(self, values, db):
        self._db = db
        self._values = dict(values)
        self.items = [Doc(item, db) if isinstance(item, dict) else item for item in self._values.get("items", [])]
        self._values["items"] = self.items
        for key, value in self._values.items():
            setattr(self, key, value)

    def insert(self, ignore_permissions=False):
        doctype = self._values.get("doctype")
        name = self._values.get("name") or self._values.get("jti") or f"{doctype}-1"
        self._values["name"] = name
        self.name = name
        self._db.rows[(doctype, name)] = self._values
        return self


def fake_frappe(monkeypatch):
    db = MemoryDB()
    po = Doc({
        "doctype": "Purchase Order", "name": "PO-2026-0042", "supplier": "SUP-SAMPLE",
        "supplier_email": "buyer@northstar.example", "helios_confirmation_status": "Pending",
        "items": [{"doctype": "Purchase Order Item", "name": "POI-1", "item_code": "SAMPLE-BRACKET", "qty": 2, "schedule_date": "2026-10-30"}],
    }, db)
    so = Doc({
        "doctype": "Sales Order", "name": "SO-2026-0007", "customer_name": "Fictional Acme",
        "status": "To Deliver", "transaction_date": "2026-10-23", "delivery_date": "2026-11-14",
        "per_delivered": 0, "items": [{"name": "SOI-1", "item_code": "SAMPLE-BRACKET", "item_name": "Sample bracket", "qty": 2, "uom": "Nos", "schedule_date": "2026-11-14", "delivered_qty": 0}],
    }, db)
    supplier = {"doctype": "Supplier", "name": "SUP-SAMPLE", "email_id": "buyer@northstar.example"}
    db.rows[("Purchase Order", po.name)] = po._values
    db.rows[("Sales Order", so.name)] = so._values
    db.rows[("Supplier", supplier["name"])] = supplier
    for item in po.items:
        db.rows[("Purchase Order Item", item.name)] = item._values
    for item in so.items:
        item._values["parent"] = so.name
        db.rows[("Sales Order Item", item.name or "SOI-1")] = item._values

    def get_doc(value, name=None):
        if isinstance(value, dict):
            return Doc(value, db)
        if name is None:
            name = value
            value = "Purchase Order"
        row = db.rows.get((value, name))
        if row is None:
            raise KeyError((value, name))
        return Doc(row, db)

    def get_all(doctype, filters=None, fields=None, pluck=None, limit=None):
        filters = filters or {}
        matches = []
        for (row_doctype, name), row in db.rows.items():
            if row_doctype != doctype:
                continue
            ok = True
            for key, expected in filters.items():
                if isinstance(expected, (list, tuple)):
                    op, val = expected[0], expected[1]
                    if op == "<" and not row.get(key, "") < val:
                        ok = False
                elif row.get(key) != expected:
                    ok = False
            if ok:
                selected = {"name": name, **row} if fields is None else {field: (name if field == "name" else row.get(field)) for field in fields}
                matches.append(selected)
        if pluck:
            return [row.get(pluck) for row in matches]
        return matches[:limit] if limit else matches

    fake = types.SimpleNamespace(
        conf={"encryption_key": "test-key"}, db=db, get_doc=get_doc, get_all=get_all,
        local=types.SimpleNamespace(form_dict={}), utils=types.SimpleNamespace(get_url=lambda: "https://site.invalid", get_system_timezone=lambda: "Europe/Helsinki"),
        get_conf=lambda: {"encryption_key": "test-key"}, log_error=lambda *args: None,
        get_traceback=lambda: "traceback",
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    return fake, po, so


def test_supplier_link_confirmation_updates_po_line_and_audit(monkeypatch):
    fake, po, _ = fake_frappe(monkeypatch)
    issued = ensure_confirmation(po)
    assert issued["link"].startswith("https://erp.example.test/helios/confirm?token=")
    raw, _ = issue_token("Purchase Order", po.name, "supplier_confirmation", datetime.now(timezone.utc) + timedelta(days=1))
    result = confirm_from_token(raw, True, "2026-11-04", source="link")
    assert result == {"status": "Confirmed", "schedule_date": "2026-11-04", "idempotent": False}
    assert fake.db.rows[("Purchase Order", po.name)]["helios_confirmation_status"] == "Confirmed"
    assert fake.db.rows[("Purchase Order Item", "POI-1")]["schedule_date"] == "2026-11-04"
    assert any(key[0] == "Supplier PO Confirmation" for key in fake.db.rows)
    replay = confirm_from_token(raw, True, "2026-11-04", source="link")
    assert replay["idempotent"] is True


def test_supplier_email_is_sender_checked_and_message_id_is_idempotent(monkeypatch):
    fake, po, _ = fake_frappe(monkeypatch)
    ensure_confirmation(po)
    with pytest.raises(PermissionError):
        process_incoming_email("attacker@example.test", "Re: PO-2026-0042", "Confirmed 2026-11-04", "<m1>")
    first = process_incoming_email("buyer@northstar.example", "Re: PO-2026-0042", "Confirmed. ETA: 2026-11-04", "<m1>")
    second = process_incoming_email("buyer@northstar.example", "Re: PO-2026-0042", "Confirmed. ETA: 2026-11-04", "<m1>")
    assert first["processed"] is True and first["idempotent"] is False
    assert second["idempotent"] is True
    assert fake.db.rows[("Purchase Order", po.name)]["helios_supplier_schedule_date"] == "2026-11-04"


def test_customer_tracking_is_filtered_to_safe_fields(monkeypatch):
    fake, _, so = fake_frappe(monkeypatch)
    issued = ensure_tracking_link(so, "Sales Order")
    raw, _ = issue_token("Sales Order", so.name, "customer_tracking", datetime.now(timezone.utc) + timedelta(days=1))
    snapshot = tracking_snapshot(raw)
    assert issued["link"].startswith("https://erp.example.test/helios/track?token=")
    assert snapshot["customer"] == "Fictional Acme"
    assert snapshot["items"][0]["item_code"] == "SAMPLE-BRACKET"
    assert "rate" not in snapshot["items"][0]


def test_token_expiry_is_stored_in_site_time_zone(monkeypatch):
    from zoneinfo import ZoneInfo
    from helios_order_visibility.services.supplier import _token_is_current
    from helios_order_visibility.services.tokens import decode_and_validate

    fake, po, _ = fake_frappe(monkeypatch)
    expires = datetime(2030, 1, 15, 22, 30, tzinfo=timezone.utc)
    raw, jti = issue_token("Purchase Order", po.name, "supplier_confirmation", expires)
    stored = fake.db.rows[("Helios Tracking Token", jti)]["expires_at"]
    assert stored == expires.astimezone(ZoneInfo("Europe/Helsinki")).strftime("%Y-%m-%d %H:%M:%S") == "2030-01-16 00:30:00"
    assert decode_and_validate(raw, "supplier_confirmation")["name"] == po.name
    assert _token_is_current({"expires_at": stored})
    assert not _token_is_current({"expires_at": "2020-01-01 00:00:00"})


def test_supplier_view_shows_owning_company_and_lines(monkeypatch):
    from helios_order_visibility.services.supplier import supplier_confirmation_view

    fake, po, _ = fake_frappe(monkeypatch)
    fake.db.rows[("Purchase Order", po.name)]["company"] = "EXM"
    fake.db.rows[("Company", "EXM")] = {"company_name": "Example Manufacturing Oy"}
    raw, _ = issue_token("Purchase Order", po.name, "supplier_confirmation", datetime.now(timezone.utc) + timedelta(days=1))
    view = supplier_confirmation_view(raw)
    assert view["company"] == "Example Manufacturing Oy"
    assert view["status"] == "Pending"
    assert view["requested_date"] == "2026-10-30"
    assert [item["item_code"] for item in view["items"]] == ["SAMPLE-BRACKET"]
