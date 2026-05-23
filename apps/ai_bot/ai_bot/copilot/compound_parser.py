# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Split compound requests and parse multiple intents."""

import re

from ai_bot.copilot.entity_resolver import extract_delete_target, extract_update_fields
from ai_bot.copilot.intent_parser import _clarification, _default_fields, _detect_analysis_type, _detect_report_type
from ai_bot.copilot.synonyms import detect_action_in_clause, normalize_message
from ai_bot.utils.doctype_discovery import discover_doctype, get_config
from ai_bot.utils.doctypes_map import resolve_doctype
from ai_bot.utils.field_filters import parse_field_filters
from ai_bot.utils.filters import merge_filters, parse_customer_filter, parse_period_filters, parse_status_filters


SPLIT_PATTERN = re.compile(
	r"\s+(?:also|and then|then|;\s*|&\s+and\s+|\s+&\s+)",
	re.I,
)


def split_clauses(raw: str) -> list[str]:
	parts = [p.strip() for p in SPLIT_PATTERN.split(raw) if p.strip()]
	return parts if len(parts) > 1 else [raw.strip()]


def parse_intents(message: str, context: dict | None = None) -> list[dict]:
	"""Parse one or more intents from a message (handles compound commands)."""
	raw = (message or "").strip()
	context = dict(context or {})
	context.setdefault("raw_message", raw)

	if not raw:
		return [_clarification("Please enter a request.")]

	clauses = split_clauses(raw)
	global_doctype = _resolve_doctype_from_message(raw, context)
	shared_entity = extract_delete_target(raw)

	intents = []
	for clause in clauses:
		intent = _parse_single_clause(clause, raw, context, global_doctype, shared_entity)
		if intent:
			intents.append(intent)

	if not intents:
		return [_clarification("I could not understand that request.")]

	# Single clarification only
	if len(intents) == 1:
		return intents

	if all(i.get("action") == "clarification" for i in intents):
		return intents

	return intents


def _parse_single_clause(
	clause: str,
	full_raw: str,
	context: dict,
	global_doctype: str | None,
	shared_entity: str | None,
) -> dict:
	text = normalize_message(clause)
	action = detect_action_in_clause(text)
	if not action:
		return _clarification(f"I could not detect an action in: \"{clause.strip()}\"")

	doctype = _resolve_doctype_from_message(clause, context) or global_doctype
	if not doctype and action not in ("report", "analyze", "summarize"):
		return _clarification("Please specify which document type (e.g. Customer, Sales Order).")

	intent = {
		"action": action,
		"doctype": doctype or "",
		"filters": {},
		"data": {},
		"fields": _default_fields(doctype) if doctype else [],
		"message": "",
		"status": "success",
	}

	if doctype:
		config = get_config(doctype)
		date_field = config.get("date_field") or "creation"
		intent["filters"] = merge_filters(
			parse_status_filters(text),
			parse_period_filters(text, date_field),
			parse_customer_filter(clause),
			parse_field_filters(text, doctype),
		)

	if action == "delete":
		intent["status"] = "warning"
		target = extract_delete_target(clause) or shared_entity
		if target:
			intent["filters"]["_hint"] = target
	elif action == "update":
		filter_hints, data = extract_update_fields(clause, doctype or "Customer")
		intent["data"].update(data)
		if filter_hints:
			intent["filters"].update(filter_hints)
		elif shared_entity and not intent["data"]:
			intent["filters"]["_hint"] = shared_entity
		# Target for update: entity from delete clause if same message
		if shared_entity and not intent["filters"].get("customer_name"):
			intent["filters"]["_hint"] = shared_entity
	elif action == "create":
		from ai_bot.copilot.intent_parser import _extract_create_data

		intent["data"] = _extract_create_data(text, doctype, clause)
	elif action == "read":
		if re.search(r"\b(how many|count|number of)\b", text):
			intent["read_type"] = "count"
		elif re.search(r"\b(total value|sum of|total amount|aggregate)\b", text):
			intent["read_type"] = "aggregate"
		else:
			intent["read_type"] = "list"
		search_q = _extract_clause_search(clause)
		if search_q:
			intent["search_query"] = search_q
	elif action == "report":
		intent["report_type"] = _detect_report_type(text)
	elif action == "analyze":
		intent["analysis_type"] = _detect_analysis_type(text)

	return intent


def _extract_clause_search(clause: str) -> str | None:
	match = re.search(
		r"\b(?:named|called|matching|like|containing|with name)\s+['\"]?([^'\"]+?)['\"]?(?:\s*$|\s+and)",
		clause,
		re.I,
	)
	if match:
		return match.group(1).strip()
	return None


def _resolve_doctype_from_message(text: str, context: dict) -> str | None:
	for source in (text, context.get("raw_message") or ""):
		found = resolve_doctype(source) or discover_doctype(source)
		if found:
			return found
	if context.get("doctype"):
		return context["doctype"]
	return None
