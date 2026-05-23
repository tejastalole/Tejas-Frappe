# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Resolve ERP records from natural-language hints (names, titles, doc IDs)."""

import re

import frappe

from ai_bot.utils.create_sales_order import resolve_customer, resolve_item_code


def resolve_record(doctype: str, hint: str) -> str | None:
	"""Find document name from a human hint like 'Tejas' or 'CUST-0001'."""
	if not hint or not doctype:
		return None

	hint = hint.strip().strip('"\'')
	if not hint:
		return None

	if frappe.db.exists(doctype, hint):
		return hint

	meta = frappe.get_meta(doctype)
	search_fields = _search_fields(meta, doctype)

	for field in search_fields:
		name = frappe.db.get_value(
			doctype,
			{field: ["like", f"%{hint}%"]},
			"name",
			order_by="modified desc",
		)
		if name:
			return name

	if doctype == "Customer":
		return resolve_customer(hint)
	if doctype == "Item":
		return resolve_item_code(hint)

	return None


def _search_fields(meta, doctype: str) -> list[str]:
	fields = []
	title_field = meta.get_title_field()
	if title_field and meta.has_field(title_field):
		fields.append(title_field)

	priority = {
		"Customer": ["customer_name", "name"],
		"Item": ["item_name", "item_code", "name"],
		"Employee": ["employee_name", "name"],
		"Lead": ["lead_name", "company_name", "name"],
		"Supplier": ["supplier_name", "name"],
	}
	for f in priority.get(doctype, []):
		if meta.has_field(f) and f not in fields:
			fields.append(f)

	if "name" not in fields:
		fields.append("name")
	return fields


def extract_delete_target(raw: str) -> str | None:
	"""e.g. 'delete the Tejas' -> 'Tejas'"""
	patterns = [
		r"\bdelete(?:\s+the|\s+this|\s+that)?\s+(.+?)(?:\s+also\b|\s+and\b|$)",
		r"\bremove(?:\s+the)?\s+(.+?)(?:\s+also\b|\s+and\b|$)",
		r"\bdrop(?:\s+the)?\s+(.+?)(?:\s+also\b|\s+and\b|$)",
	]
	for pattern in patterns:
		match = re.search(pattern, raw, re.I)
		if match:
			target = _clean_entity(match.group(1))
			if target:
				return target
	return None


def extract_update_fields(raw: str, doctype: str) -> tuple[dict, dict]:
	"""Return (filters_hint, data) from update phrases."""
	data = {}
	filters = {}

	# change/set/update field to value
	field_patterns = [
		(
			r"\b(?:change|set|update|modify|edit)\s+(?:the\s+)?(\w+)\s+(?:to|as|into|=)\s*['\"]?([^'\"]+?)['\"]?(?:\s+customer|\s*$)",
			None,
		),
		(
			r"\b(?:change|set|update)\s+(?:the\s+)?(\w+)\s+['\"]?([^'\"]+?)['\"]?\s*$",
			None,
		),
		(
			r"\bchange\s+(?:the\s+)?id\s+(?:to\s+)?['\"]?([^'\"]+?)['\"]?(?:\s+customer|\s*$)",
			"customer_name",
		),
		(
			r"\b(?:rename|call)\s+(?:it|them|this)?\s*(?:to|as)\s+['\"]?([^'\"]+?)['\"]?",
			"customer_name",
		),
	]

	for pattern, forced_field in field_patterns:
		match = re.search(pattern, raw, re.I)
		if not match:
			continue
		if forced_field:
			value = match.group(1).strip().strip('"\'')
			data[forced_field] = value
			break
		field_label = match.group(1).strip().lower()
		value = match.group(2).strip().strip('"\'')
		fieldname = map_field_label(doctype, field_label)
		if fieldname:
			data[fieldname] = value
			break

	# from X to Y
	match = re.search(
		r"\b(?:change|update)\s+(?:customer\s+)?(?:name\s+)?from\s+['\"]?([^'\"]+?)['\"]?\s+(?:to|as)\s+['\"]?([^'\"]+?)['\"]?",
		raw,
		re.I,
	)
	if match:
		filters["customer_name"] = match.group(1).strip()
		if doctype == "Customer":
			data["customer_name"] = match.group(2).strip()

	return filters, data


def map_field_label(doctype: str, label: str) -> str | None:
	label = label.lower().replace(" ", "_")
	aliases = {
		"id": "customer_name",
		"customer_id": "name",
		"name": "customer_name",
		"customer_name": "customer_name",
		"email": "email_id",
		"phone": "mobile_no",
		"mobile": "mobile_no",
		"qty": "qty",
		"quantity": "qty",
		"rate": "rate",
		"price": "rate",
	}

	field = aliases.get(label, label)
	meta = frappe.get_meta(doctype)
	if meta.has_field(field):
		return field

	# id on Customer often means display name
	if label in ("id", "customer_id") and doctype == "Customer" and meta.has_field("customer_name"):
		return "customer_name"

	return None


def _clean_entity(text: str) -> str | None:
	text = text.strip().strip('"\'')
	text = re.sub(r"\s+(customer|item|employee|lead)s?\s*$", "", text, flags=re.I)
	text = re.sub(r"^(the|a|an)\s+", "", text, flags=re.I)
	return text.strip() if text else None
