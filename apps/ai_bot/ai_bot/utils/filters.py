# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe.utils import (
	add_days,
	add_months,
	get_first_day,
	get_last_day,
	getdate,
	nowdate,
)

STATUS_MAP = {
	"draft": 0,
	"drafts": 0,
	"submitted": 1,
	"confirmed": 1,
	"cancelled": 2,
	"canceled": 2,
}


def parse_status_filters(message: str) -> dict:
	filters = {}
	if re.search(r"\boverdue\b", message, re.I):
		filters["status"] = "Overdue"
	if re.search(r"\b(pending)\b", message, re.I) and "invoice" in message.lower():
		filters["status"] = "Unpaid"
	if re.search(r"\b(draft|drafts)\b", message):
		filters["docstatus"] = 0
	elif re.search(r"\b(submitted|confirmed)\b", message):
		filters["docstatus"] = 1
	elif re.search(r"\b(cancelled|canceled)\b", message):
		filters["docstatus"] = 2
	return filters


def parse_period_filters(message: str, date_field: str) -> dict:
	today = getdate(nowdate())
	message = message.lower()

	if re.search(r"\btoday\b", message):
		return {date_field: today}
	if re.search(r"\byesterday\b", message):
		return {date_field: add_days(today, -1)}
	if re.search(r"\bthis week\b", message):
		start = add_days(today, -today.weekday())
		return {date_field: ["between", [start, today]]}
	if re.search(r"\blast week\b", message):
		end = add_days(today, -today.weekday() - 1)
		start = add_days(end, -6)
		return {date_field: ["between", [start, end]]}
	if re.search(r"\bthis month\b", message):
		return {date_field: ["between", [get_first_day(today), get_last_day(today)]]}
	if re.search(r"\blast month\b", message):
		last = add_months(today, -1)
		return {date_field: ["between", [get_first_day(last), get_last_day(last)]]}
	if re.search(r"\bthis year\b", message):
		return {date_field: ["between", [f"{today.year}-01-01", f"{today.year}-12-31"]]}
	if re.search(r"\b(last \d+ days?)\b", message):
		match = re.search(r"last (\d+) days?", message)
		if match:
			days = int(match.group(1))
			return {date_field: ["between", [add_days(today, -days), today]]}

	# "created" often means record creation date
	if re.search(r"\bcreated\b", message) and date_field != "creation":
		if re.search(r"\bthis month\b", message):
			return {"creation": ["between", [get_first_day(today), get_last_day(today)]]}

	return {}


def parse_customer_filter(message: str) -> dict:
	match = re.search(
		r"(?:for|of)\s+(?:customer\s+)?['\"]?([^'\"?\n]+?)['\"]?(?:\s*\?|$|\s+this|\s+in|\s+with)",
		message,
		re.I,
	)
	if not match:
		match = re.search(r"customer\s+['\"]?([^'\"?\n]+)['\"]?", message, re.I)
	if not match:
		return {}

	name_part = match.group(1).strip()
	if name_part.lower() in ("sales", "purchase", "order", "orders", "invoice"):
		return {}

	customer = frappe.db.get_value(
		"Customer",
		{"customer_name": ["like", f"%{name_part}%"]},
		"name",
		order_by="modified desc",
	)
	if not customer:
		customer = frappe.db.get_value("Customer", name_part, "name")
	return {"customer": customer} if customer else {}


def merge_filters(*filter_dicts: dict) -> dict:
	result = {}
	for f in filter_dicts:
		result.update(f)
	return result


def filters_summary(filters: dict, doctype: str) -> str:
	from frappe import _

	parts = []
	if filters.get("docstatus") == 0:
		parts.append(_("draft"))
	elif filters.get("docstatus") == 1:
		parts.append(_("submitted"))
	elif filters.get("docstatus") == 2:
		parts.append(_("cancelled"))

	config = __import__("ai_bot.utils.doctypes_map", fromlist=["get_config"]).get_config(doctype)
	date_field = config.get("date_field") or "creation"
	if date_field in filters or "creation" in filters:
		field = date_field if date_field in filters else "creation"
		val = filters.get(field)
		if isinstance(val, list) and val[0] == "between":
			parts.append(_("in selected period"))
		elif val:
			parts.append(_("on {0}").format(val))

	if filters.get("customer"):
		parts.append(_("for {0}").format(filters["customer"]))

	for field in ("grand_total", "net_total", "qty"):
		if field not in filters:
			continue
		val = filters[field]
		label = field.replace("_", " ")
		if isinstance(val, (list, tuple)) and len(val) == 2:
			op, num = val
			sym = {">": ">", "<": "<"}.get(op, op)
			parts.append(_("{0} {1} {2}").format(label, sym, num))
		else:
			parts.append(_("{0} = {1}").format(label, val))

	return ", ".join(parts) if parts else ""
