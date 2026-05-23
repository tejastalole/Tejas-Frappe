# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.skills.base import BotResponse
from ai_bot.utils.doctype_discovery import discover_doctype, get_config
from ai_bot.utils.doctypes_map import list_supported_doctypes, resolve_doctype
from ai_bot.utils.filters import filters_summary, merge_filters, parse_customer_filter


def resolve_doctype_from_message(message: str) -> str | None:
	return extract_doctype_from_message(message)


def extract_doctype_from_message(message: str) -> str | None:
	"""Find DocType from the current message (longest alias match wins)."""
	message_lower = message.lower()

	# Strip filter / condition tail before alias scan
	base = re.split(r"\s+(?:whose|where|with|having|for which)\s+", message_lower, maxsplit=1)[0]
	base = re.sub(
		r"^(?:how many|count|number of|total value of|sum of)\s+",
		"",
		base,
		flags=re.I,
	)
	base = re.sub(
		r"\s+(created|exist|in the system|this month|today|last month|this week).*$",
		"",
		base,
	)

	for doctype_name in list_supported_doctypes():
		config = get_config(doctype_name)
		for alias in sorted(config.get("aliases", []), key=len, reverse=True):
			if re.search(rf"\b{re.escape(alias)}\b", base):
				return doctype_name

	# Any DocType in the system (dynamic)
	found = discover_doctype(base) or discover_doctype(message_lower)
	if found:
		return found

	# Also try full message for multi-word aliases after "how many"
	phrase_match = re.search(
		r"(?:how many|count|number of|total(?:\s+value)?\s+of)\s+(.+?)(?:\s+(?:are|is|were|was)\b|\?|$)",
		message_lower,
		re.I,
	)
	if phrase_match:
		phrase = phrase_match.group(1).strip()
		phrase = re.sub(r"\s+(?:whose|where|with|having).*$", "", phrase)
		doctype = resolve_doctype(phrase)
		if doctype:
			return doctype

	return None


def is_refinement_query(message: str) -> bool:
	"""True when message only refines filters, not a new DocType question."""
	if extract_doctype_from_message(message):
		return False
	refine_patterns = [
		r"\b(only|just|filter)\b",
		r"\b(this month|last month|today|this week|yesterday)\b",
		r"\b(draft|submitted|cancelled)\b",
		r"\bfor customer\b",
		r"^(only|draft|submitted|this month)",
		r"\bgrand total\b",
		r"\bwhose\b",
		r"\bwhere\b",
	]
	return any(re.search(p, message, re.I) for p in refine_patterns)


def resolve_doctype_for_query(message: str, context: dict | None = None) -> str | None:
	"""Prefer DocType named in the current message; use context only for refinements."""
	extracted = extract_doctype_from_message(message)
	if extracted:
		return extracted
	if context and context.get("doctype") and is_refinement_query(message):
		return context.get("doctype")
	return extracted or (context or {}).get("doctype")


def build_filters(message: str, doctype: str, base_filters: dict | None = None) -> dict:
	from ai_bot.utils.field_filters import parse_field_filters
	from ai_bot.utils.filters import parse_period_filters, parse_status_filters

	config = get_config(doctype)
	date_field = config.get("date_field") or "creation"
	return merge_filters(
		base_filters or {},
		parse_status_filters(message),
		parse_period_filters(message, date_field),
		parse_customer_filter(message),
		parse_field_filters(message, doctype),
	)


def list_action(doctype: str, filters: dict) -> dict:
	from ai_bot.utils.serialize import json_safe_filters

	return {
		"label": _("Open List"),
		"type": "list",
		"doctype": doctype,
		"filters": json_safe_filters(filters),
	}


def create_action(doctype: str) -> dict:
	return {
		"label": _("Create {0}").format(frappe.unscrub(doctype)),
		"type": "create",
		"doctype": doctype,
	}


def form_action(doctype: str, name: str) -> dict:
	return {
		"label": _("Open {0}").format(name),
		"type": "form",
		"doctype": doctype,
		"name": name,
	}


def format_count_reply(doctype: str, count: int, filters: dict) -> str:
	label = frappe.unscrub(doctype)
	summary = filters_summary(filters, doctype)
	if summary:
		return _("There are <b>{0}</b> {1} ({2}).").format(count, label, summary)
	return _("There are <b>{0}</b> {1} in the system.").format(count, label)


def format_sum_reply(doctype: str, total: float, filters: dict) -> str:
	label = frappe.unscrub(doctype)
	formatted = frappe.format_value(total, {"fieldtype": "Currency"})
	summary = filters_summary(filters, doctype)
	if summary:
		return _("Total value of {0} is <b>{1}</b> ({2}).").format(label, formatted, summary)
	return _("Total value of {0} is <b>{1}</b>.").format(label, formatted)
