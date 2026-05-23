# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _
from frappe.utils import add_days, flt, today

import erpnext


def parse_create_so_params(message: str) -> dict | None:
	"""Extract customer, item, qty, rate from a natural-language create request."""
	text = message.strip()
	lower = text.lower()

	customer = None
	for pattern in (
		r"for\s+customer\s+(.+?)(?:\s+item\b|\s+qty\b|\s+quantity\b|\s+rate\b|$)",
		r"customer\s+(?:is\s+)?(.+?)(?:\s+item\b|\s+qty\b|\s+quantity\b|\s+rate\b|$)",
	):
		match = re.search(pattern, lower, re.I)
		if match:
			customer = match.group(1).strip()
			break

	item_code = _extract_item_code(text, lower)
	qty_match = re.search(
		r"(?:with\s+)?(?:qty|quantity)\s+(?:is\s+)?(\d+(?:\.\d+)?)",
		lower,
		re.I,
	)
	rate_match = re.search(r"rate\s+(?:is\s+)?(\d+(?:\.\d+)?)", lower, re.I)

	if not item_code:
		return None

	if not customer:
		customer = get_default_customer()

	if not customer:
		return {
			"customer": None,
			"item_code": item_code,
			"qty": flt(qty_match.group(1)) if qty_match else 1,
			"rate": flt(rate_match.group(1)) if rate_match else None,
			"needs_customer": True,
		}

	return {
		"customer": customer,
		"item_code": item_code,
		"qty": flt(qty_match.group(1)) if qty_match else 1,
		"rate": flt(rate_match.group(1)) if rate_match else None,
	}


def _extract_item_code(text: str, lower: str) -> str | None:
	patterns = [
		r"\badd\s+(?:a\s+)?item\s+([A-Za-z0-9_-]+)",
		r"\binside\s+add\s+(?:a\s+)?item\s+([A-Za-z0-9_-]+)",
		r"\bwith\s+item\s+([A-Za-z0-9_-]+)",
		r"\bitem\s+(?:is\s+)?([A-Za-z0-9_-]+)",
		r"\badd\s+(?:a\s+)?([A-Za-z0-9_-]+)\s+with\s+(?:qty|quantity)\b",
	]
	for pattern in patterns:
		match = re.search(pattern, text, re.I)
		if match:
			code = match.group(1).strip()
			if code.lower() not in ("sales", "order", "inside", "a", "an", "the", "new", "create"):
				return code
	return None


def get_default_customer() -> str | None:
	"""Default customer for SO when user omits customer name."""
	customer = frappe.db.get_value(
		"Customer",
		{"disabled": 0, "is_internal_customer": 0},
		"name",
		order_by="modified desc",
	)
	if customer:
		return customer
	return frappe.db.get_value("Customer", {}, "name", order_by="creation asc")


def resolve_customer(name: str) -> str | None:
	name = name.strip()
	customer = frappe.db.get_value(
		"Customer",
		{"customer_name": ["like", f"%{name}%"]},
		"name",
		order_by="modified desc",
	)
	if customer:
		return customer
	if frappe.db.exists("Customer", name):
		return name
	return frappe.db.get_value(
		"Customer",
		{"name": ["like", f"%{name}%"]},
		"name",
		order_by="modified desc",
	)


def resolve_item_code(code: str) -> str | None:
	code = code.strip()
	if frappe.db.exists("Item", code):
		return code
	item = frappe.db.get_value(
		"Item",
		{"item_code": ["like", code]},
		"name",
	)
	if item:
		return item
	return frappe.db.get_value(
		"Item",
		{"item_name": ["like", f"%{code}%"]},
		"name",
		order_by="modified desc",
	)


def get_default_warehouse(company: str, item_code: str) -> str | None:
	warehouse = frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		"default_warehouse",
	)
	if warehouse:
		return warehouse
	warehouse = frappe.get_cached_value("Stock Settings", None, "default_warehouse")
	if warehouse:
		return warehouse
	return frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")


def create_sales_order(customer: str, item_code: str, qty: float, rate: float | None) -> frappe.Document:
	if not frappe.has_permission("Sales Order", "create"):
		frappe.throw(_("You do not have permission to create Sales Orders."), frappe.PermissionError)

	customer_id = resolve_customer(customer)
	if not customer_id:
		frappe.throw(_("Customer <b>{0}</b> was not found.").format(customer))

	item_id = resolve_item_code(item_code)
	if not item_id:
		frappe.throw(_("Item <b>{0}</b> was not found.").format(item_code))

	company = erpnext.get_default_company()
	if not company:
		company = frappe.db.get_value("Company", {"disabled": 0}, "name")
	if not company:
		frappe.throw(_("No active Company found. Please set a default company."))

	so = frappe.new_doc("Sales Order")
	so.company = company
	so.customer = customer_id
	so.transaction_date = today()
	so.delivery_date = add_days(today(), 7)

	item_row = {"item_code": item_id, "qty": flt(qty)}
	if rate is not None:
		item_row["rate"] = flt(rate)

	if frappe.db.get_value("Item", item_id, "is_stock_item"):
		warehouse = get_default_warehouse(company, item_id)
		if warehouse:
			item_row["warehouse"] = warehouse

	so.append("items", item_row)
	so.flags.ignore_permissions = False
	so.insert()

	return so
