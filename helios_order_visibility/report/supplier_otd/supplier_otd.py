"""Supplier on-time-delivery report and late-line workspace data."""

from datetime import date, datetime

import frappe


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return frappe.utils.getdate(value)


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": "Purchase Order", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 90},
        {"label": "Schedule Date", "fieldname": "schedule_date", "fieldtype": "Date", "width": 110},
        {"label": "Received Date", "fieldname": "received_date", "fieldtype": "Date", "width": 110},
        {"label": "Days Late", "fieldname": "days_late", "fieldtype": "Int", "width": 90},
        {"label": "OTD", "fieldname": "otd_status", "fieldtype": "Data", "width": 90},
    ]
    conditions = ["po.docstatus = 1", "poi.schedule_date is not null"]
    values = {}
    if filters.get("supplier"):
        conditions.append("po.supplier = %(supplier)s")
        values["supplier"] = filters["supplier"]
    if filters.get("from_date"):
        conditions.append("poi.schedule_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("poi.schedule_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]
    query = f"""
        select po.name as purchase_order, po.supplier, poi.item_code, poi.qty,
               poi.schedule_date, min(pr.posting_date) as received_date
        from `tabPurchase Order` po
        join `tabPurchase Order Item` poi on poi.parent = po.name
        left join `tabPurchase Receipt Item` pri on pri.purchase_order = po.name
            and pri.purchase_order_item = poi.name
        left join `tabPurchase Receipt` pr on pr.name = pri.parent and pr.docstatus = 1
        where {' and '.join(conditions)}
        group by po.name, po.supplier, poi.item_code, poi.qty, poi.schedule_date
        order by poi.schedule_date asc, po.name asc
    """
    rows = frappe.db.sql(query, values, as_dict=True)
    for row in rows:
        schedule = _date(row.get("schedule_date"))
        row["schedule_date"] = schedule
        if row.get("received_date"):
            received = _date(row["received_date"])
            row["received_date"] = received
            row["days_late"] = max(0, (received - schedule).days)
            row["otd_status"] = "On time" if row["days_late"] == 0 else "Late"
        else:
            today = _date(frappe.utils.getdate())
            row["days_late"] = max(0, (today - schedule).days) if today > schedule else 0
            row["otd_status"] = "Late open" if row["days_late"] else "Open"
    if filters.get("otd_status"):
        rows = [row for row in rows if row["otd_status"] == filters["otd_status"]]
    return columns, rows
