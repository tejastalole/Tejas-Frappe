# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from ai_bot.utils.doctypes_map import DOCTYPE_CONFIG, get_config as get_static_config


def infer_doctype_config(doctype: str) -> dict:
	"""Build query metadata from DocType meta when not in static map."""
	static = DOCTYPE_CONFIG.get(doctype)
	if static:
		return static

	meta = frappe.get_meta(doctype)
	date_field = "creation"
	for candidate in ("transaction_date", "posting_date", "date", "due_date", "creation"):
		if meta.has_field(candidate):
			date_field = candidate
			break

	amount_field = None
	for candidate in ("grand_total", "base_grand_total", "total", "amount", "net_total"):
		if meta.has_field(candidate):
			amount_field = candidate
			break

	aliases = [doctype.lower(), frappe.scrub(doctype).replace("_", " ")]
	return {
		"aliases": aliases,
		"date_field": date_field,
		"amount_field": amount_field,
	}


def get_config(doctype: str) -> dict:
	return infer_doctype_config(doctype)


def discover_doctype(phrase: str) -> str | None:
	"""Resolve any DocType the user can read, not only predefined aliases."""
	if not phrase:
		return None

	phrase = phrase.strip()
	clean = phrase.lower()
	for plural, singular in (
		("sales orders", "sales order"),
		("purchase orders", "purchase order"),
		("sales invoices", "sales invoice"),
		("purchase invoices", "purchase invoice"),
		("delivery notes", "delivery note"),
		("quotations", "quotation"),
		("customers", "customer"),
		("employees", "employee"),
		("leads", "lead"),
		("items", "item"),
	):
		clean = clean.replace(plural, singular)

	clean = re.sub(
		r"^(?:how many|count|number of|list|show|display|get|fetch|total value of|sum of)\s+",
		"",
		clean,
		flags=re.I,
	)
	clean = re.sub(r"\s+(whose|where|with|having|for which).*$", "", clean, flags=re.I)
	clean = re.sub(r"\s+(are|is|were|was|exist|created).*$", "", clean, flags=re.I)
	clean = clean.strip().lower()

	# Exact DocType name
	for candidate in (phrase.title(), phrase.replace(" ", " ").title()):
		name = _normalize_doctype_name(candidate)
		if name and frappe.db.exists("DocType", name) and _can_read(name):
			return name

	# Title case: "sales order" -> "Sales Order", "employee" -> "Employee"
	title_name = " ".join(word.capitalize() for word in clean.split())
	name = _normalize_doctype_name(title_name)
	if name:
		return name

	# Search DocType table
	like = f"%{clean.replace(' ', '%')}%"
	candidates = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0, "name": ["like", like]},
		fields=["name", "module"],
		order_by="name asc",
		limit=20,
	)

	readable = [d.name for d in candidates if _can_read(d.name)]
	if len(readable) == 1:
		return readable[0]
	if readable:
		# Prefer exact word match in name
		for name in readable:
			if clean in name.lower() or clean in frappe.scrub(name).replace("_", " "):
				return name
		return readable[0]

	return None


def _normalize_doctype_name(name: str) -> str | None:
	name = name.strip()
	if not name or not frappe.db.exists("DocType", name):
		return None
	if _can_read(name):
		return name
	return None


def _can_read(doctype: str) -> bool:
	try:
		return frappe.has_permission(doctype, "read")
	except Exception:
		return False


def get_accessible_doctypes(module: str | None = None, search: str | None = None, limit: int = 200) -> list[dict]:
	filters = {"istable": 0, "issingle": 0}
	if module:
		filters["module"] = ["like", f"%{module}%"]
	if search:
		filters["name"] = ["like", f"%{search}%"]

	rows = frappe.get_all(
		"DocType",
		filters=filters,
		fields=["name", "module"],
		order_by="module asc, name asc",
		limit=limit,
	)
	return [r for r in rows if _can_read(r.name)]


def get_module_summary() -> list[dict]:
	"""DocType counts grouped by module."""
	doctypes = get_accessible_doctypes(limit=500)
	module_counts: dict[str, int] = {}
	for dt in doctypes:
		mod = dt.module or "Other"
		module_counts[mod] = module_counts.get(mod, 0) + 1
	return sorted(
		[{"module": m, "count": c} for m, c in module_counts.items()],
		key=lambda x: -x["count"],
	)


def count_doctype_records(doctype: str) -> int:
	if not _can_read(doctype):
		return 0
	try:
		return frappe.db.count(doctype)
	except Exception:
		return 0


def get_recent_records(doctype: str, limit: int = 5) -> list[dict]:
	if not _can_read(doctype):
		return []
	meta = frappe.get_meta(doctype)
	fields = ["name"]
	if meta.has_field("title"):
		fields.append("title")
	else:
		tf = meta.get_title_field()
		if tf and meta.has_field(tf):
			fields.append(tf)
	order_by = "modified desc"
	if meta.has_field("modified"):
		order_by = "modified desc"
	return frappe.get_list(doctype, fields=fields, limit=limit, order_by=order_by)
