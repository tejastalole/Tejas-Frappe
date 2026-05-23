# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Natural language → structured copilot JSON intent."""

import json
import re

from ai_bot.copilot.synonyms import detect_action, map_status, normalize_message
from ai_bot.utils.doctype_discovery import discover_doctype
from ai_bot.utils.doctypes_map import resolve_doctype
from ai_bot.utils.field_filters import parse_field_filters
from ai_bot.utils.filters import merge_filters, parse_customer_filter, parse_period_filters, parse_status_filters
from ai_bot.utils.doctype_discovery import get_config


def parse_intent(message: str, context: dict | None = None) -> dict:
	"""Return structured JSON intent (single or compound wrapper)."""
	from ai_bot.copilot.compound_parser import parse_intents

	intents = parse_intents(message, context)
	if len(intents) == 1:
		intent = intents[0]
		_enrich_intent(intent, message, context)
		return intent

	return {
		"action": "compound",
		"doctype": "",
		"filters": {},
		"data": {},
		"fields": [],
		"intents": intents,
		"message": "",
		"status": "success",
	}


def _enrich_intent(intent: dict, message: str, context: dict | None) -> None:
	"""Doc name from raw message + context merge for refinements."""
	context = context or {}
	raw = (message or "").strip()
	text = normalize_message(raw)
	name_from_raw = _extract_doc_name(raw)
	doctype = intent.get("doctype")

	if doctype and name_from_raw:
		intent.setdefault("filters", {}).update(name_from_raw)

	if context.get("doctype") == doctype and context.get("filters"):
		if not intent.get("filters"):
			intent["filters"] = dict(context["filters"])
		elif _is_refinement(text):
			intent["filters"] = merge_filters(context["filters"], intent["filters"])


def intent_to_json(intent: dict) -> str:
	return json.dumps(intent, default=str)


def _clarification(message: str) -> dict:
	return {
		"action": "clarification",
		"doctype": "",
		"filters": {},
		"data": {},
		"fields": [],
		"message": message,
		"status": "need_input",
	}


def _resolve_doctype(text: str, context: dict) -> str | None:
	for source in (text, context.get("raw_message") or text):
		found = resolve_doctype(source) or discover_doctype(source)
		if found:
			return found
	if context.get("doctype") and _is_refinement(text):
		return context["doctype"]
	return None


def _is_refinement(text: str) -> bool:
	return bool(
		re.search(
			r"\b(only|just|this month|last month|today|draft|submitted|whose|where)\b",
			text,
		)
	)


def _default_fields(doctype: str | None) -> list:
	if not doctype:
		return ["name"]
	fields = ["name"]
	config = get_config(doctype)
	if config.get("amount_field"):
		fields.append(config["amount_field"])
	meta_fields = {"Customer": ["customer_name"], "Item": ["item_name"], "Employee": ["employee_name"]}
	for f in meta_fields.get(doctype, []):
		if f not in fields:
			fields.append(f)
	return fields


def _extract_doc_name(raw: str) -> dict:
	match = re.search(r"\b([A-Z]{2,}[-][A-Z0-9-]+)\b", raw)
	if match:
		return {"name": match.group(1)}
	return {}


def _extract_create_data(text: str, doctype: str | None, raw: str) -> dict:
	data = {}
	if not doctype:
		return data

	if doctype == "Customer":
		match = re.search(
			r"(?:create\s+)?(?:customer|client)\s+(.+?)$",
			raw,
			re.I,
		)
		if match:
			data["customer_name"] = match.group(1).strip()

	elif doctype == "Employee":
		match = re.search(r"employee\s+(.+?)$", raw, re.I)
		if match:
			data["employee_name"] = match.group(1).strip().title()

	elif doctype == "Sales Order":
		from ai_bot.utils.create_sales_order import parse_create_so_params

		params = parse_create_so_params(raw)
		if params and not params.get("needs_customer"):
			data = {
				"customer": params.get("customer"),
				"items": [
					{
						"item_code": params.get("item_code"),
						"qty": params.get("qty"),
						"rate": params.get("rate"),
					}
				],
			}

	elif doctype == "Quotation":
		customer = parse_customer_filter(text).get("customer")
		if customer:
			data["customer"] = customer
		item_match = re.search(r"(\d+)\s+([a-z0-9_-]+)", text, re.I)
		if item_match:
			data["items"] = [
				{"item_code": item_match.group(2).upper(), "qty": float(item_match.group(1))}
			]

	elif doctype == "Item":
		item_match = re.search(
			r"(?:create\s+)?(?:a\s+)?(.+?)\s+item(?:\s+qty\s+(?:is\s+)?(\d+(?:\.\d+)?))?",
			raw,
			re.I,
		)
		if item_match:
			data["item_name"] = item_match.group(1).strip().title()
			if item_match.group(2):
				data["qty"] = float(item_match.group(2))
		else:
			match = re.search(r"item\s+(.+?)$", raw, re.I)
			if match:
				data["item_name"] = match.group(1).strip().title()

	return data


def _extract_update_data(text: str, raw: str) -> dict:
	data = {}
	match = re.search(r"(?:to|as|into)\s+(.+?)$", raw, re.I)
	if match:
		val = match.group(1).strip()
		if "customer" in text:
			data["customer_name"] = val
		elif "name" in text:
			data["name"] = val
	return data


def _extract_update_filters(text: str, raw: str) -> dict:
	filters = {}
	match = re.search(r"from\s+(.+?)\s+(?:to|as)", raw, re.I)
	if match and "customer" in text:
		filters["customer_name"] = match.group(1).strip()
	return filters


def _detect_report_type(text: str) -> str:
	if "sales" in text:
		return "sales_summary"
	if "purchase" in text:
		return "purchase_summary"
	return "summary"


def _detect_analysis_type(text: str) -> str:
	if "month" in text:
		return "monthly_sales"
	return "general"
