from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from typing import Any

from .common import field, now_utc, public_base_url
from .tokens import TOKEN_DOCTYPE, decode_and_validate, issue_token, revoke_token

PO_PATTERN = re.compile(r"\b(?:PO[-\s]?[A-Z0-9-]+|Purchase\s+Order\s*[:#]?\s*(?:PO[-\s]?)?[A-Z0-9-]+)\b", re.I)
DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
CONFIRM_WORDS = re.compile(r"\b(confirm(?:ed|ation)?|accept(?:ed|ance)?|yes|approved?)\b", re.I)
# Do not treat ordinary prose such as "no problem" or a quoted "no-login
# link" as a rejection. A reply must contain an explicit negative decision.
REJECT_WORDS = re.compile(r"\b(reject(?:ed|ion)?|declin(?:e|ed)|cannot|can't|unable\s+to\s+(?:confirm|accept)|do\s+not\s+(?:confirm|accept)|not\s+(?:confirmed|accepted))\b", re.I)


def _frappe():
    import frappe
    return frappe


def _get_expiry_days():
    frappe = _frappe()
    try:
        value = frappe.db.get_single_value("Helios Settings", "supplier_link_expiry_days")
        return max(1, min(int(value or 7), 90))
    except Exception:
        return 7


def _supplier_email(doc):
    frappe = _frappe()
    email = field(doc, "supplier_email") or field(doc, "contact_email")
    if not email and field(doc, "supplier"):
        try:
            email = frappe.db.get_value("Supplier", field(doc, "supplier"), "email_id")
        except Exception:
            email = None
    return (email or "").strip().lower()


def _active_po_token(po_name):
    frappe = _frappe()
    rows = frappe.get_all(TOKEN_DOCTYPE, filters={"reference_doctype": "Purchase Order", "reference_name": po_name, "purpose": "supplier_confirmation", "status": "Active"}, fields=["name", "expires_at"])
    return rows[0] if rows else None


def _token_is_current(row):
    """Check the stored expiry as well as the Active flag.

    The scheduler normally marks expired rows, but guest links must remain
    safe between scheduler runs too.
    """
    if not row:
        return False
    expires_at = row.get("expires_at")
    if not expires_at:
        return False
    try:
        value = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def ensure_confirmation(doc):
    """Create one active supplier link and persist the public URL on the PO."""
    frappe = _frappe()
    po_name = field(doc, "name")
    if not po_name:
        raise ValueError("Purchase Order must have a name")
    existing = _active_po_token(po_name)
    if existing:
        return {**existing, "link": field(doc, "helios_confirmation_link")}
    expires = now_utc() + timedelta(days=_get_expiry_days())
    raw, jti = issue_token("Purchase Order", po_name, "supplier_confirmation", expires, {"supplier_email": _supplier_email(doc)})
    base = public_base_url(frappe)
    # Frappe's public web pages receive the capability through form_dict. A
    # query parameter keeps the saved link on the real, tested page route.
    link = f"{base}/helios/confirm?token={raw}"
    values = {"helios_confirmation_status": "Pending", "helios_confirmation_link": link}
    for key, value in values.items():
        if hasattr(doc, "db_set"):
            doc.db_set(key, value, update_modified=False)
        else:
            frappe.db.set_value("Purchase Order", po_name, key, value, update_modified=False)
    return {"name": jti, "expires_at": expires.isoformat(), "link": link}


def revoke_confirmation(doc):
    frappe = _frappe()
    for row in frappe.get_all(TOKEN_DOCTYPE, filters={"reference_doctype": "Purchase Order", "reference_name": field(doc, "name"), "purpose": "supplier_confirmation", "status": "Active"}, pluck="name"):
        revoke_token(row)
    if hasattr(doc, "db_set"):
        doc.db_set("helios_confirmation_status", "Revoked", update_modified=False)


def _po_name_from_text(subject, body):
    match = PO_PATTERN.search(f"{subject or ''}\n{body or ''}")
    if not match:
        return None
    value = match.group(0)
    value = re.sub(r"^Purchase\s+Order\s*[:#]?\s*", "", value, flags=re.I)
    value = re.sub(r"^PO[-\s]?", "PO-", value, flags=re.I)
    return value.strip()


def parse_confirmation_reply(subject: str, body: str) -> dict[str, Any]:
    """Parse a constrained reply format without using an LLM or executing content."""
    text = f"{subject or ''}\n{body or ''}".strip()
    decision = "confirmed" if CONFIRM_WORDS.search(text) and not REJECT_WORDS.search(text) else "rejected" if REJECT_WORDS.search(text) else None
    schedule_date = DATE_PATTERN.search(text)
    return {"purchase_order": _po_name_from_text(subject, body), "decision": decision, "schedule_date": schedule_date.group(1) if schedule_date else None}


def _validate_schedule(value):
    if value in (None, ""):
        return None
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("schedule_date must be YYYY-MM-DD") from exc
    return str(value)


def _set_po_fields(po_name, values):
    frappe = _frappe()
    for key, value in values.items():
        frappe.db.set_value("Purchase Order", po_name, key, value, update_modified=True)


def _set_item_schedule(po, schedule_date):
    """Mirror a supplier's confirmed date to every open PO line.

    ERPNext's OTD report is line based. The app-owned PO field keeps the audit
    value while the standard child schedule_date drives receipts and reports.
    """
    if not schedule_date:
        return
    frappe = _frappe()
    for item in getattr(po, "items", []) or []:
        if getattr(item, "name", None):
            frappe.db.set_value("Purchase Order Item", item.name, "schedule_date", schedule_date, update_modified=False)


def _write_confirmation_audit(po, status, schedule_date, source, message_id=None, note=None):
    """Create one immutable-ish app record for the state transition.

    The PO custom fields remain the operational read model.  This record is
    deliberately best-effort for sites upgraded from the first release where
    the DocType may not yet have been created; the PO update must still win.
    """
    frappe = _frappe()
    values = {
        "doctype": "Supplier PO Confirmation",
        "purchase_order": field(po, "name"),
        "supplier": field(po, "supplier"),
        "supplier_email": _supplier_email(po),
        "status": status,
        "schedule_date": schedule_date,
        "confirmation_source": source,
        "confirmed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "message_id": message_id,
        "note": note,
    }
    try:
        frappe.get_doc(values).insert(ignore_permissions=True)
    except Exception:
        # Do not roll back a confirmed PO because an optional audit insert is
        # unavailable during a partial migration.  The server log remains the
        # signal for an administrator to complete the migration.
        if hasattr(frappe, "log_error"):
            frappe.log_error(frappe.get_traceback(), "Helios confirmation audit insert")


def confirm_from_token(raw_token: str, confirmed: bool = True, schedule_date: str | None = None, note: str | None = None, source: str = "link", message_id: str | None = None):
    claims = decode_and_validate(raw_token, "supplier_confirmation")
    po_name = claims["name"]
    schedule_date = _validate_schedule(schedule_date)
    frappe = _frappe()
    po = frappe.get_doc("Purchase Order", po_name)
    current = field(po, "helios_confirmation_status") or "Pending"
    target = "Confirmed" if confirmed else "Rejected"
    if current in {"Confirmed", "Rejected"}:
        old_date = field(po, "helios_supplier_schedule_date")
        if current != target or (schedule_date and str(old_date or "") != schedule_date):
            raise ValueError("Purchase Order confirmation already has a different decision")
        return {"status": current, "schedule_date": old_date, "idempotent": True}
    values = {
        "helios_confirmation_status": target,
        "helios_supplier_confirmed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "helios_supplier_schedule_date": schedule_date,
        "helios_confirmation_source": source,
    }
    if message_id:
        values["helios_confirmation_message_id"] = message_id
    _set_po_fields(po_name, values)
    _set_item_schedule(po, schedule_date)
    _write_confirmation_audit(po, target, schedule_date, source, message_id, note)
    return {"status": target, "schedule_date": schedule_date, "idempotent": False}


def process_incoming_email(sender: str, subject: str, body: str, message_id: str | None = None):
    """Process a supplier reply; sender and message id are checked for replay safety."""
    parsed = parse_confirmation_reply(subject, body)
    if not parsed["purchase_order"] or not parsed["decision"]:
        return {"processed": False, "reason": "unrecognised_reply", "parsed": parsed}
    frappe = _frappe()
    po_name = parsed["purchase_order"]
    if not frappe.db.exists("Purchase Order", po_name):
        return {"processed": False, "reason": "purchase_order_not_found", "purchase_order": po_name}
    po = frappe.get_doc("Purchase Order", po_name)
    expected = _supplier_email(po)
    actual = parseaddr(sender or "")[1].strip().lower()
    if not expected:
        return {"processed": False, "reason": "supplier_email_missing", "purchase_order": po_name}
    if actual != expected:
        raise PermissionError("supplier sender does not match Purchase Order supplier email")
    if message_id:
        duplicate = frappe.db.get_value("Purchase Order", po_name, "helios_confirmation_message_id")
        if duplicate == message_id:
            return {"processed": True, "idempotent": True, "purchase_order": po_name}
    token = _active_po_token(po_name)
    if not _token_is_current(token):
        return {"processed": False, "reason": "no_active_confirmation", "purchase_order": po_name}
    # Reconstructing a token is intentionally impossible: email replies can only
    # confirm while the active link exists and use the PO-specific server lookup.
    raw = frappe.local.form_dict.get("confirmation_token") if getattr(frappe.local, "form_dict", None) else None
    if raw:
        result = confirm_from_token(raw, parsed["decision"] == "confirmed", parsed["schedule_date"], source="email", message_id=message_id)
    else:
        # Internal Communication hooks are trusted after sender + PO checks and
        # update through the same idempotent state transition.
        current = field(po, "helios_confirmation_status") or "Pending"
        target = "Confirmed" if parsed["decision"] == "confirmed" else "Rejected"
        if current in {"Confirmed", "Rejected"}:
            old_date = field(po, "helios_supplier_schedule_date")
            if current != target or (parsed["schedule_date"] and str(old_date or "") != parsed["schedule_date"]):
                raise ValueError("Purchase Order confirmation already has a different decision")
            result = {"status": current, "idempotent": True, "schedule_date": field(po, "helios_supplier_schedule_date")}
        else:
            schedule_date = _validate_schedule(parsed["schedule_date"])
            _set_po_fields(po_name, {"helios_confirmation_status": target, "helios_supplier_confirmed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "helios_supplier_schedule_date": schedule_date, "helios_confirmation_source": "email", "helios_confirmation_message_id": message_id})
            _set_item_schedule(po, schedule_date)
            _write_confirmation_audit(po, target, schedule_date, "email", message_id)
            result = {"status": target, "idempotent": False, "schedule_date": parsed["schedule_date"]}
    return {"processed": True, "purchase_order": po_name, **result}
