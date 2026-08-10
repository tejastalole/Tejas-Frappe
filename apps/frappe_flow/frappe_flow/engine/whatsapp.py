# Copyright (c) 2026, Tejas and contributors
# MIT License

import json
import re

import frappe
import requests
from frappe import _


def send_whatsapp_message(phone, message, provider=None, credential_name=None):
	phone = normalize_phone(phone)
	message = (message or "").strip()
	if not message:
		frappe.throw(_("WhatsApp message is required."))

	cred = _get_credential(credential_name)
	provider_key = _resolve_provider(provider, cred.provider)

	if provider_key == "twilio":
		return _send_twilio(phone, message, cred)
	if provider_key == "meta":
		return _send_meta(phone, message, cred)

	frappe.throw(_("Unsupported WhatsApp provider: {0}").format(cred.provider))


def normalize_phone(phone, default_country_code="91"):
	phone = (phone or "").strip()
	if not phone:
		frappe.throw(_("Phone number is required for WhatsApp."))

	phone = re.sub(r"[\s\-().]", "", phone)
	if phone.startswith("whatsapp:"):
		phone = phone.split(":", 1)[1]

	if phone.startswith("+"):
		return phone.lstrip("+")

	if phone.startswith("00"):
		return phone[2:]

	if re.match(r"^[6-9]\d{9}$", phone):
		return f"{default_country_code}{phone}"

	if phone.startswith(default_country_code) and len(phone) >= 11:
		return phone

	return phone.lstrip("+")


def _resolve_provider(node_provider, cred_provider):
	provider = (node_provider or cred_provider or "").lower()
	if "twilio" in provider:
		return "twilio"
	if "meta" in provider:
		return "meta"
	frappe.throw(_("Provider must be Twilio or Meta Cloud API."))


def _get_credential(credential_name):
	if not credential_name:
		frappe.throw(
			_(
				"WhatsApp credential is required. Create an FF Flow Credential "
				"(Twilio or Meta Cloud API) and select it on the WhatsApp node."
			)
		)
	if not frappe.db.exists("FF Flow Credential", credential_name):
		frappe.throw(_("FF Flow Credential not found: {0}").format(credential_name))
	return frappe.get_doc("FF Flow Credential", credential_name)


def _load_config(cred):
	config = cred.config_json or {}
	if isinstance(config, str):
		try:
			config = json.loads(config)
		except json.JSONDecodeError:
			frappe.throw(_("Invalid JSON in credential Config JSON for {0}").format(cred.name))
	return config or {}


def _send_twilio(phone, message, cred):
	account_sid = cred.get_password("api_key")
	auth_token = cred.get_password("api_secret")
	if not account_sid or not auth_token:
		frappe.throw(_("Twilio credential needs API Key (Account SID) and API Secret (Auth Token)."))

	config = _load_config(cred)
	from_number = config.get("from_number") or config.get("whatsapp_from")
	if not from_number:
		frappe.throw(
			_('Twilio credential Config JSON must include "from_number", e.g. "whatsapp:+14155238886"')
		)

	from_addr = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
	to_addr = f"whatsapp:+{phone}" if not phone.startswith("+") else f"whatsapp:{phone}"

	url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
	response = requests.post(
		url,
		auth=(account_sid, auth_token),
		data={"From": from_addr, "To": to_addr, "Body": message},
		timeout=30,
	)

	if response.status_code >= 400:
		_log_provider_error("Twilio", response)
		frappe.throw(_("Twilio WhatsApp failed: {0}").format(_extract_error(response)))

	data = response.json()
	return {"provider": "Twilio", "sid": data.get("sid"), "status": data.get("status"), "to": phone}


def _send_meta(phone, message, cred):
	access_token = cred.get_password("api_key") or cred.get_password("api_secret")
	if not access_token:
		frappe.throw(_("Meta credential needs API Key (Access Token)."))

	config = _load_config(cred)
	phone_number_id = config.get("phone_number_id")
	if not phone_number_id:
		frappe.throw(_('Meta credential Config JSON must include "phone_number_id".'))

	api_version = config.get("api_version") or "v21.0"
	url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
	payload = {
		"messaging_product": "whatsapp",
		"to": phone,
		"type": "text",
		"text": {"preview_url": False, "body": message},
	}

	response = requests.post(
		url,
		headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
		json=payload,
		timeout=30,
	)

	if response.status_code >= 400:
		_log_provider_error("Meta", response)
		frappe.throw(_("Meta WhatsApp failed: {0}").format(_extract_error(response)))

	data = response.json()
	message_id = (data.get("messages") or [{}])[0].get("id")
	return {"provider": "Meta Cloud API", "message_id": message_id, "to": phone}


def _extract_error(response):
	try:
		data = response.json()
	except ValueError:
		return response.text[:500]

	if isinstance(data, dict):
		if data.get("message"):
			return data["message"]
		if data.get("error"):
			err = data["error"]
			if isinstance(err, dict):
				return err.get("message") or str(err)
			return str(err)
	return response.text[:500]


def _log_provider_error(provider, response):
	frappe.log_error(
		title=f"{provider} WhatsApp API Error",
		message=f"Status: {response.status_code}\n{response.text[:2000]}",
	)
