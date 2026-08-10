# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Public APIs to send WhatsApp messages."""

from __future__ import annotations

import json

import frappe
from frappe import _

from whatsapp_integration.utils.client import (
	build_template_payload,
	build_text_payload,
	dumps,
	extract_message_id,
	get_settings,
	normalize_phone,
	post_messages,
)


def _parse_components(components):
	if components is None or components == "":
		return None
	if isinstance(components, (list, dict)):
		return components if isinstance(components, list) else [components]
	if isinstance(components, str):
		try:
			parsed = json.loads(components)
		except json.JSONDecodeError:
			frappe.throw(_("Invalid components JSON"))
		if isinstance(parsed, dict):
			return [parsed]
		if isinstance(parsed, list):
			return parsed
		frappe.throw(_("components must be a JSON list or object"))
	frappe.throw(_("Invalid components value"))


@frappe.whitelist()
def send_whatsapp_message(
	to: str,
	message: str | None = None,
	template: str | None = None,
	language_code: str = "en_US",
	components=None,
	preview_url: int | bool = 0,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
):
	"""
	Send a WhatsApp text or template message.

	:param to: Recipient phone (digits / E.164 without +)
	:param message: Free-form text (required when template is empty)
	:param template: Approved template name
	:param language_code: Template language code
	:param components: Template components (JSON string or list)
	:param preview_url: Enable link preview for text messages
	:param reference_doctype: Optional linked DocType
	:param reference_name: Optional linked document name
	"""
	frappe.only_for(("System Manager", "WhatsApp Manager"))

	settings, _token = get_settings()
	to_number = normalize_phone(to, settings.default_country_code)

	if not template and not message:
		frappe.throw(_("Either message or template is required."))

	components_list = _parse_components(components) if template else None
	is_template = bool(template)

	doc = frappe.get_doc(
		{
			"doctype": "WhatsApp Message",
			"status": "Queued",
			"direction": "Outgoing",
			"message_type": "Template" if is_template else "Text",
			"to": to_number,
			"message": message,
			"template_name": template,
			"language_code": language_code if is_template else None,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	try:
		if is_template:
			payload = build_template_payload(
				to=to_number,
				template=template,
				language_code=language_code or "en_US",
				components=components_list,
			)
		else:
			payload = build_text_payload(
				to=to_number,
				message=message,
				preview_url=bool(int(preview_url)),
			)

		api_response = post_messages(payload)
		message_id = extract_message_id(api_response)

		doc.db_set(
			{
				"status": "Sent",
				"message_id": message_id,
				"raw_response": dumps(api_response),
				"error_message": "",
			},
			update_modified=True,
		)
		frappe.db.commit()

		return {
			"ok": True,
			"name": doc.name,
			"message_id": message_id,
			"to": to_number,
			"response": api_response,
		}
	except Exception as exc:
		doc.db_set(
			{
				"status": "Failed",
				"error_message": str(exc)[:1400],
			},
			update_modified=True,
		)
		frappe.db.commit()
		raise


@frappe.whitelist()
def get_whatsapp_settings_status():
	"""Return whether WhatsApp is configured (without exposing the token)."""
	frappe.only_for(("System Manager", "WhatsApp Manager"))
	settings = frappe.get_single("WhatsApp Settings")
	has_token = bool(settings.get_password("access_token"))
	return {
		"enabled": bool(settings.enabled),
		"has_token": has_token,
		"has_phone_number_id": bool(settings.phone_number_id),
		"app_id": settings.app_id,
		"api_version": settings.api_version,
	}
