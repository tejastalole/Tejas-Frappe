# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _

from ai_bot.api.conversation import load_conversation, save_exchange
from ai_bot.skills.registry import process_message

@frappe.whitelist()
def ask(message: str, conversation_id: str | None = None) -> dict:
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Please enter a question."))

	context = {}
	if conversation_id:
		loaded = load_conversation(conversation_id)
		if loaded:
			context = loaded.get("context") or {}

	result = process_message(message, context)
	result_dict = result.to_dict()

	new_conversation_id = save_exchange(
		conversation_id,
		message,
		result_dict["reply"],
		result_dict.get("actions"),
		result_dict.get("context"),
	)

	out = {
		"reply": result_dict["reply"],
		"actions": result_dict.get("actions") or [],
		"context": result_dict.get("context") or {},
		"conversation_id": new_conversation_id,
	}
	if result_dict.get("intent"):
		out["intent"] = result_dict["intent"]
	return out


@frappe.whitelist()
def parse_query(message: str) -> dict:
	"""Return structured copilot JSON only (no execution)."""
	from ai_bot.copilot.intent_parser import parse_intent

	return parse_intent((message or "").strip())


@frappe.whitelist()
def execute_query(message: str, conversation_id: str | None = None) -> dict:
	"""Parse and execute; returns intent JSON plus execution result."""
	from ai_bot.copilot.executor import execute_intent
	from ai_bot.copilot.intent_parser import parse_intent

	message = (message or "").strip()
	if not message:
		frappe.throw(_("Please enter a request."))

	context = {}
	if conversation_id:
		loaded = load_conversation(conversation_id)
		if loaded:
			context = loaded.get("context") or {}

	intent = parse_intent(message, context)
	result = execute_intent(intent, message)
	intent["status"] = result.get("status", intent.get("status"))

	return {
		"intent": intent,
		"result": {
			"status": result.get("status"),
			"message": result.get("message"),
			"data": result.get("data"),
		},
		"actions": result.get("actions") or [],
	}


@frappe.whitelist()
def get_welcome() -> str:
	from ai_bot.copilot.persona import get_welcome_message

	return get_welcome_message()


@frappe.whitelist()
def get_conversation(conversation_id: str) -> dict:
	data = load_conversation(conversation_id)
	if not data:
		frappe.throw(_("Conversation not found."))
	return data
