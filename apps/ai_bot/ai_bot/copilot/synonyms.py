# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Normalize synonyms and Hindi keywords to standard ERP terms."""

import re

# Word-level replacements (order matters — longer phrases first)
PHRASE_MAP = [
	("sales invoices", "sales invoice"),
	("purchase invoices", "purchase invoice"),
	("sales invoice", "sales invoice"),
	("purchase invoice", "purchase invoice"),
	("sales order", "sales order"),
	("purchase order", "purchase order"),
	("delivery note", "delivery note"),
	("work order", "work order"),
	("bill", "purchase invoice"),
	("invoice", "sales invoice"),
	("client", "customer"),
	("buyer", "customer"),
	("vendor", "supplier"),
	("staff", "employee"),
	("product", "item"),
	("products", "items"),
	("quote", "quotation"),
	("pending invoices", "overdue sales invoice"),
	("bikri", "sales"),
	("bikari", "sales"),
	("pending approvals", "pending approval"),
	("pending purchase orders", "purchase order"),
	("pending quotations", "quotation"),
	("unpaid invoices", "sales invoice"),
	("low stock items", "item"),
	("material request", "material request"),
	("leave application", "leave application"),
	("salary slip", "salary slip"),
	("job applicant", "job applicant"),
	("आज की सेल्स", "sales invoice"),
	("सेल्स रिपोर्ट", "sales report"),
]

ACTION_PHRASES = {
	"create": ["create", "make", "new", "add", "generate", "banao", "banao", "create karo"],
	"read": [
		"show",
		"list",
		"get",
		"fetch",
		"display",
		"find",
		"search",
		"dikhao",
		"dikha",
		"dekho",
		"how many",
		"count",
		"number of",
	],
	"update": ["update", "change", "modify", "edit", "set", "badlo"],
	"delete": ["delete", "remove", "drop"],
	"report": ["report", "summary report"],
	"analyze": ["analyze", "analysis", "insight", "trend"],
	"summarize": ["summarize", "summary", "overview"],
	"approve": ["approve", "submit", "confirm", "manzoor", "submit karo"],
	"reject": ["reject", "reject karo", "aswikar"],
	"cancel": ["cancel", "cancel karo"],
	"email": ["email", "mail", "send email"],
	"notify": ["notify", "notification", "alert"],
}

STATUS_MAP = {
	"pending": "Draft",
	"draft": "Draft",
	"submitted": "Submitted",
	"overdue": "Overdue",
	"paid": "Paid",
	"unpaid": "Unpaid",
	"open": "Open",
	"closed": "Closed",
}


def normalize_message(message: str) -> str:
	text = (message or "").strip().lower()
	for src, dest in PHRASE_MAP:
		text = re.sub(rf"\b{re.escape(src)}\b", dest, text)
	text = re.sub(r"\s+", " ", text)
	return text


# When multiple verbs appear, prefer destructive/explicit actions first
ACTION_PRIORITY = [
	"delete",
	"create",
	"update",
	"reject",
	"approve",
	"cancel",
	"email",
	"notify",
	"report",
	"analyze",
	"summarize",
	"read",
]


def detect_action(text: str) -> str | None:
	return detect_action_in_clause(text)


def detect_action_in_clause(text: str) -> str | None:
	text = text.lower()
	found = []
	for action in ACTION_PRIORITY:
		phrases = ACTION_PHRASES.get(action, [])
		for phrase in sorted(phrases, key=len, reverse=True):
			if phrase in text:
				found.append(action)
				break
	if not found:
		return None
	# Prefer delete/create over update when user says "delete ... also change ..."
	return found[0]


def detect_all_actions(text: str) -> list[str]:
	text = text.lower()
	actions = []
	for action in ACTION_PRIORITY:
		for phrase in ACTION_PHRASES.get(action, []):
			if phrase in text:
				actions.append(action)
				break
	return actions


def map_status(value: str) -> str:
	return STATUS_MAP.get(value.lower(), value)
