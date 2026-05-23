# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Permission-aware read access to data across the Frappe site."""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money

from ai_bot.utils.doctype_discovery import _can_read, get_accessible_doctypes, get_config

# Business DocTypes searched first (site-wide search)
PRIORITY_DOCTYPES = [
	"Customer",
	"Supplier",
	"Item",
	"Lead",
	"Opportunity",
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Purchase Order",
	"Purchase Invoice",
	"Delivery Note",
	"Employee",
	"Project",
	"Task",
	"Issue",
	"Contact",
	"Payment Entry",
	"BOM",
	"Work Order",
	"Warehouse",
	"Company",
]

SKIP_DOCTYPES = {
	"DocType",
	"DocField",
	"Custom Field",
	"Property Setter",
	"Version",
	"Error Log",
	"Access Log",
	"Activity Log",
	"Comment",
	"Communication",
	"File",
	"Scheduled Job Log",
}


def get_searchable_doctypes(limit: int = 40) -> list[str]:
	"""Readable DocTypes to scan, priority list first."""
	seen = set()
	result = []
	for dt in PRIORITY_DOCTYPES:
		if dt not in seen and _can_read(dt) and frappe.db.exists("DocType", dt):
			result.append(dt)
			seen.add(dt)
		if len(result) >= limit:
			return result

	for row in get_accessible_doctypes(limit=limit * 2):
		name = row.name
		if name in seen or name in SKIP_DOCTYPES:
			continue
		meta = frappe.get_meta(name)
		if meta.istable or meta.issingle:
			continue
		result.append(name)
		seen.add(name)
		if len(result) >= limit:
			break
	return result


def get_list_fields(doctype: str) -> list[str]:
	"""Fields to fetch for list/search display."""
	meta = frappe.get_meta(doctype)
	fields = ["name"]
	title = meta.get_title_field()
	if title and meta.has_field(title) and title not in fields:
		fields.append(title)

	for candidate in (
		"customer_name",
		"supplier_name",
		"item_name",
		"item_code",
		"employee_name",
		"lead_name",
		"status",
		"docstatus",
		"grand_total",
		"transaction_date",
		"posting_date",
		"customer",
		"supplier",
		"company",
	):
		if meta.has_field(candidate) and candidate not in fields and len(fields) < 8:
			fields.append(candidate)
	return fields


def search_in_doctype(doctype: str, query: str, limit: int = 5) -> list[dict]:
	if not _can_read(doctype) or not query or len(query) < 2:
		return []

	meta = frappe.get_meta(doctype)
	or_filters = []
	like = f"%{query}%"

	if meta.has_field("name"):
		or_filters.append(["name", "like", like])

	title = meta.get_title_field()
	if title and meta.has_field(title):
		or_filters.append([title, "like", like])

	for field in (
		"customer_name",
		"supplier_name",
		"item_name",
		"item_code",
		"employee_name",
		"lead_name",
		"company_name",
		"subject",
		"title",
	):
		if meta.has_field(field) and [field, "like", like] not in or_filters:
			or_filters.append([field, "like", like])

	if not or_filters:
		return []

	try:
		return frappe.get_list(
			doctype,
			filters={},
			or_filters=or_filters,
			fields=get_list_fields(doctype),
			limit=limit,
			order_by="modified desc",
		)
	except Exception:
		return []


def search_site_wide(query: str, max_doctypes: int = 10, per_limit: int = 4) -> list[dict]:
	"""Search query across many DocTypes; returns [{doctype, records}, ...]."""
	query = (query or "").strip()
	if len(query) < 2:
		return []

	results = []
	for doctype in get_searchable_doctypes(limit=max_doctypes + 10):
		records = search_in_doctype(doctype, query, limit=per_limit)
		if records:
			results.append({"doctype": doctype, "records": records})
		if len(results) >= max_doctypes:
			break
	return results


def get_record_summary(doctype: str, name: str) -> dict | None:
	if not _can_read(doctype) or not frappe.db.exists(doctype, name):
		return None

	doc = frappe.get_doc(doctype, name)
	meta = frappe.get_meta(doctype)
	lines = []

	for df in meta.fields:
		if df.fieldtype in (
			"Section Break",
			"Column Break",
			"Tab Break",
			"Table",
			"HTML",
			"Button",
			"Fold",
		):
			continue
		if df.fieldtype in ("Attach", "Attach Image", "Password"):
			continue
		if not df.fieldname:
			continue

		val = doc.get(df.fieldname)
		if val in (None, "", [], {}):
			continue

		if df.fieldtype == "Currency":
			val = fmt_money(flt(val), currency=doc.get("currency") or frappe.db.get_default("currency"))
		elif df.fieldtype == "Link" and isinstance(val, str):
			pass
		elif isinstance(val, (list, dict)):
			continue

		label = _(df.label or df.fieldname)
		lines.append({"label": label, "value": str(val), "fieldname": df.fieldname})
		if len(lines) >= 14:
			break

	return {
		"doctype": doctype,
		"name": name,
		"title": doc.get(meta.get_title_field() or "name") if meta.get_title_field() else name,
		"fields": lines,
	}


def get_site_overview(top_modules: int = 10, top_doctypes: int = 12) -> dict:
	from ai_bot.utils.doctype_discovery import get_module_summary

	modules = get_module_summary()[:top_modules]
	accessible = get_accessible_doctypes(limit=500)

	counts = []
	for dt in PRIORITY_DOCTYPES:
		if _can_read(dt):
			try:
				counts.append({"doctype": dt, "count": frappe.db.count(dt)})
			except Exception:
				pass

	counts.sort(key=lambda x: -x["count"])
	return {
		"total_doctypes": len(accessible),
		"modules": modules,
		"top_counts": counts[:top_doctypes],
	}


def format_record_lines(doctype: str, records: list[dict]) -> list[str]:
	lines = []
	fields = get_list_fields(doctype)
	for r in records:
		parts = [f"<b>{r.get('name')}</b>"]
		for f in fields:
			if f == "name":
				continue
			val = r.get(f)
			if val is not None and val != "":
				parts.append(f"{frappe.unscrub(f)}: {val}")
		lines.append(" — ".join(parts))
	return lines


def format_search_results(results: list[dict]) -> str:
	if not results:
		return _("No matching records found across your site.")

	sections = []
	total = sum(len(r["records"]) for r in results)
	sections.append(f"<p>{_('Found <b>{0}</b> matches across the site:').format(total)}</p>")

	for block in results[:8]:
		dt = block["doctype"]
		label = frappe.unscrub(dt)
		lines = format_record_lines(dt, block["records"])
		sections.append(f"<p><b>{label}</b></p><ul>{''.join(f'<li>{line}</li>' for line in lines)}</ul>")

	return "".join(sections)


def format_record_detail(summary: dict) -> str:
	if not summary:
		return _("Record not found.")

	rows = "".join(
		f"<tr><td style='padding:4px 8px;color:#64748b'>{f['label']}</td>"
		f"<td style='padding:4px 8px'><b>{frappe.utils.escape_html(str(f['value']))}</b></td></tr>"
		for f in summary["fields"]
	)
	return _(
		"<p><b>{0}</b> — {1}</p><table style='width:100%;font-size:13px'>{2}</table>"
	).format(summary["doctype"], summary["name"], rows)


def format_site_overview(overview: dict) -> str:
	module_lines = "<br>".join(
		f"• <b>{m['module']}</b> — {m['count']} DocTypes" for m in overview.get("modules", [])[:8]
	)
	count_lines = "<br>".join(
		f"• <b>{c['doctype']}</b>: {c['count']} records" for c in overview.get("top_counts", [])
	)
	return _(
		"<p>Your site overview (data you can access):</p>"
		"<p><b>{0}</b> accessible DocTypes</p>"
		"<p><b>Modules:</b><br>{1}</p>"
		"<p><b>Record counts:</b><br>{2}</p>"
		"<p><i>Ask: find [name], how many [DocType], list customers, show SAL-INV-00001</i></p>"
	).format(overview["total_doctypes"], module_lines, count_lines)
