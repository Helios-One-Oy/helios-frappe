from datetime import datetime, timedelta, timezone
import sys
import types

import pytest

from helios_order_visibility.services.supplier import parse_confirmation_reply
from helios_order_visibility.services.tokens import issue_token, decode_and_validate, TokenError


class _DB:
    def __init__(self):
        self.rows = {}

    def get_value(self, doctype, name, fields, as_dict=False):
        row = self.rows.get(name)
        if row is None:
            return None
        return row if as_dict else row.get(fields)

    def exists(self, doctype, name):
        return name in self.rows


def _fake_frappe(monkeypatch):
    db = _DB()

    class Doc:
        def __init__(self, values):
            self.values = values

        def insert(self, ignore_permissions=False):
            db.rows[self.values["name"]] = self.values
            return self

    fake = types.SimpleNamespace(
        conf={"encryption_key": "unit-test-encryption-key"}, db=db,
        get_doc=lambda values: Doc(values), get_conf=lambda: {"encryption_key": "unit-test-encryption-key"},
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    return fake


def test_reply_parser_requires_explicit_confirmation_and_date():
    parsed = parse_confirmation_reply("Re: PO-2026-0042", "Confirmed. ETA: 2026-11-04")
    assert {k: parsed[k] for k in ("purchase_order", "decision", "schedule_date")} == {"purchase_order": "PO-2026-0042", "decision": "confirmed", "schedule_date": "2026-11-04"}
    assert parse_confirmation_reply("PO-2026-0042", "maybe next week")["decision"] is None
    assert parse_confirmation_reply("Re: PO-2026-0042", "Confirmed, no problem. ETA 2026-11-04")["decision"] == "confirmed"
    assert parse_confirmation_reply("Re: PO-2026-0042", "The no-login link is fine")["decision"] is None


def test_signed_token_round_trip_and_tamper_rejection(monkeypatch):
    fake = _fake_frappe(monkeypatch)
    raw, jti = issue_token("Purchase Order", "PO-2026-0042", "supplier_confirmation",
        datetime.now(timezone.utc) + timedelta(days=1))
    claims = decode_and_validate(raw, "supplier_confirmation")
    assert claims["jti"] == jti
    assert fake.db.rows[jti]["jti"] == jti
    try:
        decode_and_validate(raw[:-1] + ("A" if raw[-1] != "A" else "B"), "supplier_confirmation")
    except ValueError as exc:
        assert "signature" in str(exc)
    else:
        raise AssertionError("tampered token accepted")


def test_expired_and_wrong_purpose_tokens_are_rejected(monkeypatch):
    _fake_frappe(monkeypatch)
    with pytest.raises(TokenError, match="expiry"):
        issue_token("Purchase Order", "PO-2026-0042", "supplier_confirmation",
            datetime.now(timezone.utc) - timedelta(seconds=1))
    raw, _ = issue_token("Sales Order", "SO-2026-0007", "customer_tracking",
        datetime.now(timezone.utc) + timedelta(days=1))
    with pytest.raises(TokenError, match="wrong token purpose"):
        decode_and_validate(raw, "supplier_confirmation")


def test_parser_handles_purchase_order_prefix_and_rejection():
    assert parse_confirmation_reply("Re: Purchase Order: PO-2026-0042", "No, cannot meet 2026-11-04") == {
        "purchase_order": "PO-2026-0042",
        "decision": "rejected",
        "schedule_date": "2026-11-04",
    }
