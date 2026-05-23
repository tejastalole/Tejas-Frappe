# Copyright (c) 2026, Tejas and contributors
# MIT License

import json

import frappe
from frappe import _
from frappe.utils import now

from ai_bot.utils.serialize import json_safe


def get_or_create_conversation(conversation_id: str | None = None) -> frappe.Document:
	user = frappe.session.user
	if conversation_id and frappe.db.exists("AI Bot Conversation", conversation_id):
		doc = frappe.get_doc("AI Bot Conversation", conversation_id)
		if doc.user != user and user != "Administrator":
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		return doc

	doc = frappe.get_doc(
		{
			"doctype": "AI Bot Conversation",
			"user": user,
			"title": _("Chat {0}").format(now()),
			"context_json": "{}",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def save_exchange(
	conversation_id: str | None,
	user_message: str,
	bot_reply: str,
	actions: list | None = None,
	context: dict | None = None,
) -> str:
	doc = get_or_create_conversation(conversation_id)

	doc.append(
		"messages",
		{
			"role": "User",
			"content": user_message,
		},
	)
	doc.append(
		"messages",
		{
			"role": "Bot",
			"content": bot_reply,
			"actions_json": json.dumps(json_safe(actions or [])),
		},
	)
	doc.context_json = json.dumps(json_safe(context or {}))
	doc.flags.ignore_permissions = True
	doc.save()

	return doc.name


def load_conversation(conversation_id: str) -> dict | None:
	if not conversation_id or not frappe.db.exists("AI Bot Conversation", conversation_id):
		return None

	doc = frappe.get_doc("AI Bot Conversation", conversation_id)
	if doc.user != frappe.session.user and frappe.session.user != "Administrator":
		return None

	context = {}
	try:
		context = json.loads(doc.context_json or "{}")
	except (json.JSONDecodeError, TypeError):
		pass

	messages = []
	for row in doc.messages:
		actions = []
		if row.actions_json:
			try:
				actions = json.loads(row.actions_json)
			except (json.JSONDecodeError, TypeError):
				pass
		messages.append(
			{
				"role": row.role.lower(),
				"content": row.content,
				"actions": actions,
			}
		)

	return {
		"conversation_id": doc.name,
		"context": context,
		"messages": messages,
	}
