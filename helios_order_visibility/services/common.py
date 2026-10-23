from __future__ import annotations

from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def frappe_datetime(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if hasattr(value, "strftime") else value


def field(doc, name, default=None):
    if isinstance(doc, dict):
        return doc.get(name, default)
    return getattr(doc, name, default)


def set_field(doc, name, value):
    if hasattr(doc, "set"):
        doc.set(name, value)
    else:
        setattr(doc, name, value)


def save_doc(doc):
    if hasattr(doc, "db_set"):
        doc.db_set({k: v for k, v in doc.as_dict().items() if k.startswith("helios_")}, update_modified=False)
    elif hasattr(doc, "save"):
        doc.save(ignore_permissions=True)


def as_date_string(value):
    """Return a stable ISO date for Frappe date, datetime, or string values."""
    if value in (None, ""):
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def public_base_url(frappe):
    """Use the explicit app setting when present, otherwise site URL."""
    try:
        configured = frappe.db.get_single_value("Helios Settings", "public_base_url")
    except Exception:
        configured = None
    if configured:
        return str(configured).rstrip("/")
    utils = getattr(frappe, "utils", None)
    return str(utils.get_url()).rstrip("/") if utils and hasattr(utils, "get_url") else ""
