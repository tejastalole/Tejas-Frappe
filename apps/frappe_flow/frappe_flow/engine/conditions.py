# Copyright (c)  2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe.utils import flt


OPERATORS = {
	"=": lambda a, b: str(a) == str(b),
	"!=": lambda a, b: str(a) != str(b),
	">": lambda a, b: _num(a) > _num(b),
	"<": lambda a, b: _num(a) < _num(b),
	">=": lambda a, b: _num(a) >= _num(b),
	"<=": lambda a, b: _num(a) <= _num(b),
	"contains": lambda a, b: str(b).lower() in str(a or "").lower(),
	"starts with": lambda a, b: str(a or "").lower().startswith(str(b).lower()),
	"ends with": lambda a, b: str(a or "").lower().endswith(str(b).lower()),
	"in": lambda a, b: str(a) in [x.strip() for x in str(b).split(",")],
	"not in": lambda a, b: str(a) not in [x.strip() for x in str(b).split(",")],
}


def _num(value):
	try:
		return flt(value)
	except (TypeError, ValueError):
		return 0


def get_field_value(doc, fieldname):
	if not fieldname:
		return None
	if hasattr(doc, "get"):
		return doc.get(fieldname)
	return None


def evaluate_condition(doc, node, context=None):
	"""Evaluate a single condition node."""
	config = node.get("config") or {}
	field = config.get("field_name") or config.get("field")
	operator = (config.get("operator") or "=").lower()
	value = config.get("value")
	logic = (config.get("logic") or "AND").upper()

	if config.get("type") == "role_check":
		user = context.get("user") if context else frappe.session.user
		roles = set(frappe.get_roles(user))
		return config.get("role") in roles

	fn = OPERATORS.get(operator)
	if not fn:
		return False
	return fn(get_field_value(doc, field), value)


def evaluate_condition_group(doc, nodes, edges, start_node_id, context=None):
	"""Walk condition nodes; supports simple AND/OR via node config."""
	current_id = start_node_id
	while current_id:
		node = _node_by_id(nodes, current_id)
		if not node:
			return True
		if node.get("type") == "condition":
			result = evaluate_condition(doc, node, context)
			if not result:
				return False
		elif node.get("type") in ("action", "delay", "approval", "ai"):
			return True
		next_ids = _next_nodes(edges, current_id)
		current_id = next_ids[0] if next_ids else None
	return True


def _node_by_id(nodes, node_id):
	for node in nodes:
		if node.get("id") == node_id:
			return node
	return None


def _next_nodes(edges, node_id):
	return [e.get("target") for e in edges if e.get("source") == node_id]


VARIABLE_PATTERN = re.compile(r"\{\{\s*doc\.(\w+)\s*\}\}")


def render_template(text, doc):
	if not text:
		return text

	def replacer(match):
		field = match.group(1)
		val = get_field_value(doc, field)
		return str(val if val is not None else "")

	return VARIABLE_PATTERN.sub(replacer, str(text))
