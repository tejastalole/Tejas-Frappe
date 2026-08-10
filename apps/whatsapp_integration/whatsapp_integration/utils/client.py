# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""WhatsApp Cloud API client helpers."""

from __future__ import annotations

import json
from typing import Any

import frappe
import requests
from frappe import _


def get_settings():
	settings = frappe.get_single("WhatsApp Settings")
	if not settings.enabled:
		frappe.throw(_("WhatsApp Integration is disabled. Enable it in WhatsApp Settings."))
	if not settings.phone_number_id:
		frappe.throw(_("Phone Number ID is missing in WhatsApp Settings."))
	token = settings.get_password("access_token")
	if not token:
		frappe.throw(_("Access Token is missing in WhatsApp Settings."))
	return settings, token


def normalize_phone(number: str, default_country_code: str | None = None) -> str:
	"""Return digits-only E.164 without leading +."""
	if not number:
		frappe.throw(_("Recipient phone number is required."))

	digits = "".join(ch for ch in str(number) if ch.isdigit())
	if not digits:
		frappe.throw(_("Invalid phone number: {0}").format(number))

	if default_country_code and len(digits) <= 10:
		cc = "".join(ch for ch in str(default_country_code) if ch.isdigit())
		if cc and not digits.startswith(cc):
			digits = cc + digits

	return digits


def graph_url(path: str) -> str:
	settings = frappe.get_single("WhatsApp Settings")
	base = (settings.api_base_url or "https://graph.facebook.com").rstrip("/")
	version = (settings.api_version or "v21.0").strip("/")
	path = path.lstrip("/")
	return f"{base}/{version}/{path}"


def post_messages(payload: dict[str, Any]) -> dict[str, Any]:
	"""POST to /{phone-number-id}/messages and return JSON."""
	settings, token = get_settings()
	url = graph_url(f"{settings.phone_number_id}/messages")
	headers = {
		"Authorization": f"Bearer {token}",
		"Content-Type": "application/json",
	}

	try:
		response = requests.post(url, headers=headers, json=payload, timeout=30)
	except requests.RequestException as exc:
		frappe.throw(_("WhatsApp API request failed: {0}").format(str(exc)))

	try:
		data = response.json()
	except ValueError:
		data = {"raw": response.text}

	if response.status_code >= 400:
		error = data.get("error", {}) if isinstance(data, dict) else {}
		message = error.get("message") or response.text or _("Unknown WhatsApp API error")
		frappe.throw(_("WhatsApp API error ({0}): {1}").format(response.status_code, message))

	return data


def build_text_payload(to: str, message: str, preview_url: bool = False) -> dict[str, Any]:
	return {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": to,
		"type": "text",
		"text": {
			"preview_url": bool(preview_url),
			"body": message,
		},
	}


def build_template_payload(
	to: str,
	template: str,
	language_code: str = "en_US",
	components: list | None = None,
) -> dict[str, Any]:
	payload: dict[str, Any] = {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": to,
		"type": "template",
		"template": {
			"name": template,
			"language": {"code": language_code or "en_US"},
		},
	}
	if components:
		payload["template"]["components"] = components
	return payload


def extract_message_id(api_response: dict[str, Any]) -> str | None:
	messages = api_response.get("messages") or []
	if messages and isinstance(messages, list):
		return messages[0].get("id")
	return None


def dumps(data: Any) -> str:
	return json.dumps(data, indent=2, default=str)
