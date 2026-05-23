# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Plan queries against site-wide data when intent is exploratory or ambiguous."""

import re

from ai_bot.copilot.entity_resolver import resolve_record
from ai_bot.copilot.synonyms import detect_action_in_clause, normalize_message
from ai_bot.utils.doctype_discovery import discover_doctype
from ai_bot.utils.doctypes_map import resolve_doctype


def _is_create_sales_order_message(raw: str, text: str) -> bool:
	"""Do not treat create-SO prompts as record search (e.g. 'item Bat with qty 110')."""
	return bool(
		re.search(
			r"\b(create|make|new|add)\b.+\b(sales order|sales orders)\b",
			text,
			re.I,
		)
		or re.search(r"\b(create|make|new)\b.+\bso\b", text, re.I)
	)


def plan_query(message: str, context: dict | None = None) -> dict | None:
	"""
	Return a ready-to-execute intent for site-wide reads, or None to use standard parser.
	"""
	raw = (message or "").strip()
	text = normalize_message(raw)
	context = context or {}

	if _is_create_sales_order_message(raw, text):
		return None

	if _is_site_overview(text):
		return {
			"action": "read",
			"read_type": "site_overview",
			"doctype": "",
			"filters": {},
			"data": {},
			"fields": [],
			"status": "success",
		}

	search_query = _extract_search_query(raw, text)
	if search_query and _is_site_search(text, raw):
		return {
			"action": "read",
			"read_type": "site_search",
			"search_query": search_query,
			"doctype": "",
			"filters": {},
			"data": {},
			"fields": [],
			"status": "success",
		}

	# "tell me about Tejas" / "details of customer ABC"
	detail = _plan_record_detail(raw, text, context)
	if detail:
		return detail

	# "what is Tejas" / "who is Rahul" — search then detail if one match
	if _is_who_what_query(text) and search_query:
		return {
			"action": "read",
			"read_type": "site_search",
			"search_query": search_query,
			"doctype": "",
			"filters": {},
			"data": {},
			"fields": [],
			"status": "success",
		}

	return None


def _is_site_overview(text: str) -> bool:
	return bool(
		re.search(
			r"\b("
			r"what(?:'s| is)? (?:in|inside) (?:my |the )?(?:site|frappe|erpnext|system|database)"
			r"|site (?:overview|summary)"
			r"|all (?:my )?data"
			r"|everything in (?:frappe|erpnext|the system)"
			r"|show (?:me )?(?:all )?(?:my )?(?:site|system) data"
			r")\b",
			text,
		)
	)


def _is_site_search(text: str, raw: str) -> bool:
	if re.search(r"\b(find|search|lookup|locate|look for)\b", text):
		return True
	if re.search(r"\b(give me|get me|fetch)\b.+\b(record|data|info)\b", text):
		return True
	# Named search without doctype: "show me Tejas" (not show customers)
	if re.search(r"^(show|get|display)\s+(?:me\s+)?[a-z]", text) and not resolve_doctype(text):
		if not discover_doctype(text) and not re.search(
			r"\b(customer|item|order|invoice|employee|lead)s?\b", text
		):
			return bool(_extract_search_query(raw, text))
	return False


def _is_who_what_query(text: str) -> bool:
	return bool(re.search(r"\b(who is|what is|who's|what's)\b", text))


def _extract_search_query(raw: str, text: str) -> str | None:
	patterns = [
		r"\b(?:find|search(?:\s+for)?|lookup|locate|look for)\s+(.+?)(?:\s+in\b|\s*$)",
		r"\bwho is\s+(.+?)(?:\s*\?|$)",
		r"\bwhat is\s+(.+?)(?:\s*\?|$)",
		r"\b(?:tell me about|details (?:of|for|about)|info (?:on|about))\s+(.+?)(?:\s*\?|$)",
		r"\b(?:show|get|display)\s+(?:me\s+)?(.+?)(?:\s*\?|$)",
		r"\b(?:about)\s+(.+?)(?:\s*\?|$)",
	]
	for pattern in patterns:
		match = re.search(pattern, raw, re.I)
		if match:
			q = _clean_query(match.group(1))
			if q and len(q) >= 2:
				return q
	return None


def _clean_query(q: str) -> str:
	q = q.strip().strip('"\'')
	q = re.sub(r"\s+(customer|item|employee|supplier|lead)s?\s*$", "", q, flags=re.I)
	q = re.sub(r"^(the|a|an)\s+", "", q, flags=re.I)
	stop = {"all", "records", "data", "everything", "me", "my", "site"}
	if q.lower() in stop:
		return ""
	return q.strip()


def _plan_record_detail(raw: str, text: str, context: dict) -> dict | None:
	if _is_create_sales_order_message(raw, text):
		return None

	doctype = resolve_doctype(text) or discover_doctype(text) or context.get("doctype")

	# "customer Tejas details" / "details of SAL-ORD-2026-00001"
	doc_match = re.search(r"\b([A-Z]{2,}[-][A-Z0-9-]+)\b", raw)
	if doc_match and doctype:
		return {
			"action": "read",
			"read_type": "detail",
			"doctype": doctype,
			"filters": {"name": doc_match.group(1)},
			"data": {},
			"fields": [],
			"status": "success",
		}

	if not doctype:
		return None

	hint = None
	for pattern in (
		r"\b(?:customer|item|employee|supplier|lead)\s+(.+?)(?:\s+details?|\s*\?|$)",
		r"\bdetails?\s+(?:of|for|about)\s+(.+?)(?:\s*\?|$)",
		r"\btell me about\s+(?:the\s+)?(?:customer\s+)?(.+?)(?:\s*\?|$)",
	):
		match = re.search(pattern, raw, re.I)
		if match:
			hint = _clean_query(match.group(1))
			break

	if not hint:
		return None

	name = resolve_record(doctype, hint)
	if name:
		return {
			"action": "read",
			"read_type": "detail",
			"doctype": doctype,
			"filters": {"name": name},
			"data": {},
			"fields": [],
			"status": "success",
		}

	return {
		"action": "read",
		"read_type": "site_search",
		"search_query": hint,
		"doctype": doctype,
		"filters": {},
		"data": {},
		"fields": [],
		"status": "success",
	}
