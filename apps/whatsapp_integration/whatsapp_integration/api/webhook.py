# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Meta WhatsApp Cloud API webhook handler."""

from __future__ import annotations

import json

import frappe
from frappe import _


def _settings():
	return frappe.get_single("WhatsApp Settings")


def _verify_token_ok(token: str) -> bool:
	settings = _settings()
	expected = (settings.webhook_verify_token or "").strip()
	return bool(expected) and token == expected


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def webhook(**kwargs):
	"""
	Meta webhook endpoint.

	Configure in Meta Developer Portal:
	  https://<site>/api/method/whatsapp_integration.api.webhook.webhook
	"""
	if frappe.request.method == "GET":
		return _handle_verification()
	return _handle_event()


def _handle_verification():
	"""Respond to Meta hub.challenge handshake."""
	mode = frappe.form_dict.get("hub.mode") or frappe.request.args.get("hub.mode")
	token = frappe.form_dict.get("hub.verify_token") or frappe.request.args.get("hub.verify_token")
	challenge = frappe.form_dict.get("hub.challenge") or frappe.request.args.get("hub.challenge")

	if mode == "subscribe" and _verify_token_ok(token or ""):
		frappe.local.response["type"] = "text"
		frappe.local.response["message"] = challenge
		return challenge

	frappe.throw(_("Webhook verification failed"), frappe.PermissionError)


def _handle_event():
	"""Process incoming message / status updates."""
	try:
		payload = frappe.request.get_json(force=True, silent=True) or {}
	except Exception:
		payload = {}

	if not payload and frappe.request.data:
		try:
			payload = json.loads(frappe.request.data)
		except Exception:
			payload = {}

	# Always ACK quickly so Meta does not retry forever
	frappe.enqueue(
		"whatsapp_integration.api.webhook.process_webhook_payload",
		queue="short",
		payload=payload,
		enqueue_after_commit=True,
	)

	# For whitelisted methods Frappe wraps return value; Meta expects 200
	return {"ok": True}


def process_webhook_payload(payload: dict | None = None):
	"""Background job: create / update WhatsApp Message rows from webhook."""
	payload = payload or {}
	entries = payload.get("entry") or []
	for entry in entries:
		for change in entry.get("changes") or []:
			value = change.get("value") or {}
			_process_statuses(value.get("statuses") or [])
			_process_incoming(value)


def _process_statuses(statuses: list):
	status_map = {
		"sent": "Sent",
		"delivered": "Delivered",
		"read": "Read",
		"failed": "Failed",
	}
	for status in statuses:
		wa_id = status.get("id")
		if not wa_id:
			continue
		name = frappe.db.get_value("WhatsApp Message", {"message_id": wa_id}, "name")
		if not name:
			continue

		mapped = status_map.get((status.get("status") or "").lower())
		updates = {}
		if mapped:
			updates["status"] = mapped

		errors = status.get("errors") or []
		if errors:
			updates["error_message"] = str(errors[0].get("message") or errors[0])[:1400]
			updates["status"] = "Failed"

		if updates:
			frappe.db.set_value("WhatsApp Message", name, updates)


def _process_incoming(value: dict):
	messages = value.get("messages") or []
	if not messages:
		return

	contacts = {c.get("wa_id"): c for c in (value.get("contacts") or []) if c.get("wa_id")}
	metadata = value.get("metadata") or {}
	business_phone = metadata.get("display_phone_number") or metadata.get("phone_number_id")

	for msg in messages:
		wa_id = msg.get("id")
		if not wa_id:
			continue
		if frappe.db.exists("WhatsApp Message", {"message_id": wa_id}):
			continue

		from_number = msg.get("from")
		contact = contacts.get(from_number) or {}
		profile_name = (contact.get("profile") or {}).get("name")
		msg_type = (msg.get("type") or "text").lower()
		body, mapped_type = _extract_body(msg, msg_type)

		doc = frappe.get_doc(
			{
				"doctype": "WhatsApp Message",
				"status": "Received",
				"direction": "Incoming",
				"message_type": mapped_type,
				"to": business_phone or "business",
				"from_number": from_number,
				"profile_name": profile_name,
				"message": body,
				"message_id": wa_id,
				"raw_response": json.dumps(msg, indent=2, default=str),
			}
		)
		doc.insert(ignore_permissions=True)


def _extract_body(msg: dict, msg_type: str) -> tuple[str, str]:
	type_map = {
		"text": "Text",
		"image": "Image",
		"document": "Document",
		"audio": "Audio",
		"video": "Video",
		"interactive": "Interactive",
		"button": "Button",
		"template": "Template",
	}
	mapped = type_map.get(msg_type, "Unknown")

	if msg_type == "text":
		return (msg.get("text") or {}).get("body") or "", mapped
	if msg_type == "button":
		return (msg.get("button") or {}).get("text") or "", mapped
	if msg_type == "interactive":
		interactive = msg.get("interactive") or {}
		reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
		return reply.get("title") or reply.get("id") or json.dumps(interactive), mapped
	if msg_type in ("image", "document", "audio", "video"):
		media = msg.get(msg_type) or {}
		caption = media.get("caption") or ""
		media_id = media.get("id") or ""
		filename = media.get("filename") or ""
		parts = [p for p in (caption, filename, f"media_id={media_id}" if media_id else "") if p]
		return " | ".join(parts) or msg_type, mapped

	return json.dumps(msg.get(msg_type) or msg, default=str), mapped
