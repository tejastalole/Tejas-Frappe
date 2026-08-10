# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import cint, flt, get_datetime, now_datetime


OPERATORS = {
	"=": lambda a, b: a == b,
	"!=": lambda a, b: a != b,
	">": lambda a, b: _compare(a, b) > 0,
	"<": lambda a, b: _compare(a, b) < 0,
	">=": lambda a, b: _compare(a, b) >= 0,
	"<=": lambda a, b: _compare(a, b) <= 0,
	"contains": lambda a, b: str(b).lower() in str(a or "").lower(),
	"in": lambda a, b: str(a) in [x.strip() for x in str(b).split(",")],
	"not in": lambda a, b: str(a) not in [x.strip() for x in str(b).split(",")],
}


def _compare(a, b):
	try:
		return flt(a) - flt(b)
	except (TypeError, ValueError):
		a_s, b_s = str(a or ""), str(b or "")
		if a_s == b_s:
			return 0
		return 1 if a_s > b_s else -1


def get_field_value(doc, fieldname: str):
	if not fieldname:
		return None
	if "." in fieldname:
		parts = fieldname.split(".")
		value = doc.get(parts[0])
		for part in parts[1:]:
			if value is None:
				return None
			value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
		return value
	return doc.get(fieldname)


def evaluate_conditions(doc, conditions) -> bool:
	if not conditions:
		return True

	for row in conditions:
		actual = get_field_value(doc, row.field_name)
		expected = row.value
		operator = row.operator or "="
		fn = OPERATORS.get(operator)
		if not fn:
			frappe.throw(f"Unsupported operator: {operator}")
		if not fn(actual, expected):
			return False
	return True


def find_matching_rule(doctype: str, doc):
	rules = frappe.get_all(
		"DWB Approval Rule",
		filters={"document_type": doctype, "is_active": 1},
		fields=["name"],
		order_by="modified desc",
	)
	for rule_row in rules:
		rule = frappe.get_doc("DWB Approval Rule", rule_row.name)
		if evaluate_conditions(doc, rule.conditions):
			return rule
	return None
