# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Simple ERP report summaries for the copilot."""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, getdate, add_months, nowdate


def sales_summary(months_back: int = 1) -> dict:
	if not frappe.has_permission("Sales Invoice", "read"):
		return {"error": _("No access to Sales Invoice")}

	from_date = add_months(getdate(), -months_back)
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "posting_date": [">=", from_date]},
		fields=["name", "customer", "grand_total", "outstanding_amount"],
		limit=500,
	)
	total = sum(flt(i.grand_total) for i in invoices)
	outstanding = sum(flt(i.outstanding_amount) for i in invoices)
	return {
		"count": len(invoices),
		"total": total,
		"outstanding": outstanding,
		"from_date": str(from_date),
		"records": invoices[:10],
	}


def format_sales_summary(data: dict) -> str:
	if data.get("error"):
		return data["error"]
	return _(
		"<p><b>Sales summary</b> since {0}:<br>"
		"Invoices: {1}<br>"
		"Total sales: {2}<br>"
		"Outstanding: {3}</p>"
	).format(
		data["from_date"],
		data["count"],
		fmt_money(data["total"]),
		fmt_money(data["outstanding"]),
	)


def purchase_summary(months_back: int = 1) -> dict:
	if not frappe.has_permission("Purchase Invoice", "read"):
		return {"error": _("No access to Purchase Invoice")}

	from_date = add_months(getdate(), -months_back)
	invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"docstatus": 1, "posting_date": [">=", from_date]},
		fields=["name", "supplier", "grand_total"],
		limit=500,
	)
	total = sum(flt(i.grand_total) for i in invoices)
	return {"count": len(invoices), "total": total, "from_date": str(from_date)}


def employee_count_summary() -> str:
	if not frappe.has_permission("Employee", "read"):
		return _("No access to Employee data.")
	active = frappe.db.count("Employee", {"status": "Active"})
	total = frappe.db.count("Employee")
	return _("<p><b>Employees:</b> {0} active / {1} total.</p>").format(active, total)
