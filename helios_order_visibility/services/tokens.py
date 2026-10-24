"""Opaque, expiring HMAC tokens used by guest links.

Only a SHA-256 digest is stored in the database. The raw token is returned once
when a link is created and is never needed for authenticated desk users.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any

from .common import frappe_datetime, from_site_naive, site_now, to_site_naive

TOKEN_VERSION = "1"
TOKEN_DOCTYPE = "Helios Tracking Token"
ALLOWED_PURPOSES = {"supplier_confirmation", "customer_tracking"}


class TokenError(ValueError):
    pass


def _frappe():
    import frappe
    return frappe


def _key() -> bytes:
    frappe = _frappe()
    conf = getattr(frappe, "conf", None) or (frappe.get_conf() if hasattr(frappe, "get_conf") else {})
    value = conf.get("encryption_key") if hasattr(conf, "get") else None
    if not value:
        raise TokenError("Frappe encryption_key is required for public links")
    return str(value).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(body: str) -> str:
    return _b64(hmac.new(_key(), body.encode("utf-8"), hashlib.sha256).digest())


def _utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def issue_token(doctype: str, docname: str, purpose: str, expires_at: Any, metadata: dict[str, Any] | None = None) -> tuple[str, str]:
    if purpose not in ALLOWED_PURPOSES:
        raise TokenError("unsupported token purpose")
    expires = _utc(expires_at)
    if expires <= datetime.now(timezone.utc):
        raise TokenError("token expiry must be in the future")
    jti = secrets.token_urlsafe(16)
    payload = {"v": TOKEN_VERSION, "jti": jti, "doctype": doctype, "name": docname, "purpose": purpose, "exp": int(expires.timestamp())}
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    raw = f"{TOKEN_VERSION}.{body}.{_sign(body)}"
    frappe = _frappe()
    values = {
        "doctype": TOKEN_DOCTYPE,
        "name": jti,
        "jti": jti,
        "token_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "reference_doctype": doctype,
        "reference_name": docname,
        "purpose": purpose,
        # Frappe Datetime fields hold naive values in the site's time zone,
        # so desk users see the real local expiry.
        "expires_at": frappe_datetime(to_site_naive(_frappe(), expires)),
        "status": "Active",
    }
    if metadata:
        values.update({k: v for k, v in metadata.items() if k in {"supplier_email", "customer_email", "sales_order", "delivery_note"}})
    # The DocType uses ``autoname = field:jti``.  Passing the field (rather
    # than a synthetic name) keeps inserts valid on every supported Frappe
    # version and lets Frappe derive the document name consistently.
    frappe.get_doc(values).insert(ignore_permissions=True)
    return raw, jti


def decode_and_validate(raw: str, expected_purpose: str | None = None) -> dict[str, Any]:
    if not isinstance(raw, str) or len(raw) > 512:
        raise TokenError("malformed token")
    try:
        version, body, signature = raw.split(".", 2)
        payload = json.loads(_unb64(body).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError, base64.binascii.Error) as exc:
        raise TokenError("malformed token") from exc
    if version != TOKEN_VERSION or not hmac.compare_digest(signature, _sign(body)):
        raise TokenError("invalid token signature")
    if payload.get("v") != TOKEN_VERSION or not payload.get("jti") or payload.get("purpose") not in ALLOWED_PURPOSES:
        raise TokenError("invalid token claims")
    if expected_purpose and payload["purpose"] != expected_purpose:
        raise TokenError("wrong token purpose")
    if int(payload.get("exp", 0)) <= int(datetime.now(timezone.utc).timestamp()):
        raise TokenError("token expired")
    frappe = _frappe()
    row = frappe.db.get_value(TOKEN_DOCTYPE, payload["jti"], ["token_hash", "status", "reference_doctype", "reference_name", "purpose", "expires_at"], as_dict=True)
    if not row:
        raise TokenError("unknown token")
    if row.get("status") != "Active" or not hmac.compare_digest(str(row.get("token_hash")), hashlib.sha256(raw.encode("utf-8")).hexdigest()):
        raise TokenError("revoked or invalid token")
    stored_expiry = row.get("expires_at")
    if stored_expiry:
        try:
            if from_site_naive(frappe, stored_expiry) <= datetime.now(timezone.utc):
                raise TokenError("token expired")
        except (TypeError, ValueError) as exc:
            raise TokenError("invalid token expiry") from exc
    if row.get("purpose") != payload["purpose"] or row.get("reference_doctype") != payload["doctype"] or row.get("reference_name") != payload["name"]:
        raise TokenError("token reference mismatch")
    return {**payload, "record": row}


def revoke_token(jti: str):
    frappe = _frappe()
    if frappe.db.exists(TOKEN_DOCTYPE, jti):
        frappe.db.set_value(TOKEN_DOCTYPE, jti, "status", "Revoked", update_modified=True)


def expire_due_tokens():
    frappe = _frappe()
    now = frappe_datetime(site_now(frappe))
    names = frappe.get_all(TOKEN_DOCTYPE, filters={"status": "Active", "expires_at": ["<", now]}, pluck="name")
    for name in names:
        row = frappe.db.get_value(TOKEN_DOCTYPE, name,
            ["reference_doctype", "reference_name", "purpose"], as_dict=True) or {}
        frappe.db.set_value(TOKEN_DOCTYPE, name, "status", "Expired", update_modified=True)
        # Keep the app-owned status fields useful even when the scheduler is
        # the first process to notice an expired capability.
        if row.get("purpose") == "supplier_confirmation":
            frappe.db.set_value("Purchase Order", row.get("reference_name"),
                "helios_confirmation_status", "Expired", update_modified=False)
        elif row.get("purpose") == "customer_tracking":
            frappe.db.set_value(row.get("reference_doctype"), row.get("reference_name"),
                "helios_tracking_status", "Expired", update_modified=False)
    return len(names)
