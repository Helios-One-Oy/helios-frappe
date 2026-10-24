from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


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


def site_timezone(frappe):
    """The site's System Settings time zone; UTC if it is not configured."""
    try:
        name = frappe.utils.get_system_timezone()
        return ZoneInfo(name) if name else timezone.utc
    except Exception:
        return timezone.utc


def to_site_naive(frappe, value):
    """Store an aware instant the way Frappe Datetime fields expect: site-local, naive."""
    return value.astimezone(site_timezone(frappe)).replace(tzinfo=None, microsecond=0)


def from_site_naive(frappe, value):
    """Read a Frappe Datetime value (site-local, naive) back as an aware UTC instant."""
    if not isinstance(value, datetime):
        value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=site_timezone(frappe))
    return value.astimezone(timezone.utc)


def site_now(frappe):
    """Current naive datetime in the site's time zone."""
    return to_site_naive(frappe, datetime.now(timezone.utc))


def site_today(frappe):
    return site_now(frappe).date()


def site_date_from_epoch(frappe, epoch):
    """Convert a token's UTC expiry to the site's local date."""
    if not epoch:
        return None
    return to_site_naive(frappe, datetime.fromtimestamp(int(epoch), timezone.utc)).date()

def display_date(frappe, value):
    """Format a date with the site's configured date format."""
    if value in (None, ""):
        return ""
    return frappe.utils.formatdate(value)


def display_qty(value):
    """Quantities without float noise: 24.0 -> 24, 2.5 -> 2.5."""
    if value in (None, ""):
        return ""
    return f"{float(value):g}"


def company_display_name(frappe, company=None):
    """Name of the installing company that owns the linked document."""
    if not company:
        defaults = getattr(frappe, "defaults", None)
        company = defaults.get_user_default("Company") if defaults else None
        if not company:
            company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            company = frappe.db.get_value("Company", {}, "name")
    if not company:
        return ""
    return frappe.db.get_value("Company", company, "company_name") or company
