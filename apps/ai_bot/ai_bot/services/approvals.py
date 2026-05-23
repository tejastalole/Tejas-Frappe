# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Pending drafts / submissions the user can act on."""

import frappe
from frappe import _

PENDING_DOCTYPES = [
	"Purchase Order",
	"Sales Order",
	"Purchase Invoice",
	"Sales Invoice",
	"Quotation",
	"Leave Application",
	"Expense Claim",
	"Material Request",
]


def get_pending_documents(limit_per_type: int = 5) -> list[dict]:
	"""Draft (docstatus 0) documents user may submit."""
	blocks = []
	for doctype in PENDING_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.has_permission(doctype, "read"):
			continue
		if not frappe.has_permission(doctype, "submit"):
			continue
		records = frappe.get_all(
			doctype,
			filters={"docstatus": 0},
			fields=["name", "modified"],
			order_by="modified desc",
			limit=limit_per_type,
		)
		if records:
			blocks.append({"doctype": doctype, "records": records})
	return blocks


def format_pending_html(blocks: list[dict]) -> str:
	if not blocks:
		return _("No pending documents awaiting your approval/submission.")

	lines = [f"<p>{_('Found pending documents:')}</p><ul>"]
	for block in blocks:
		for r in block["records"]:
			lines.append(
				f"<li><b>{block['doctype']}</b> {r['name']}</li>"
			)
	lines.append("</ul>")
	return "".join(lines)
