# Copyright (c) 2026, Tejas and contributors
# MIT License

import json

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, getdate, now_datetime, today

from frappe_flow.engine.conditions import get_field_value, render_template
from frappe_flow.engine.utils import resolve_email_recipients
from frappe_flow.engine.whatsapp import send_whatsapp_message


def run_action(node, doc, context=None):
	action_type = (node.get("action_type") or node.get("type") or "").lower()
	config = node.get("config") or {}

	handlers = {
		"send_email": _send_email,
		"send_whatsapp": _send_whatsapp,
		"create_task": _create_task,
		"assign_user": _assign_user,
		"webhook": _webhook,
		"api_call": _api_call,
		"create_document": _create_document,
		"update_document": _update_document,
		"create_comment": _create_comment,
		"notification": _notification,
		"delay": _schedule_delay,
		"approval": _approval_action,
		"ai": _ai_action,
	}

	handler = handlers.get(action_type) or handlers.get(node.get("type"))
	if not handler:
		frappe.throw(_("Unsupported action type: {0}").format(action_type or node.get("type")))
	return handler(config, doc, context, node)


def _send_email(config, doc, context, node):
	raw_to = render_template(config.get("to") or doc.get("owner"), doc)
	raw_cc = render_template(config.get("cc") or "", doc)
	recipients = resolve_email_recipients(raw_to)
	cc = resolve_email_recipients(raw_cc) if raw_cc else None
	subject = render_template(config.get("subject") or _("Automation Notification"), doc)
	message = render_template(config.get("message") or "", doc)
	frappe.sendmail(recipients=recipients, cc=cc, subject=subject, message=message, now=True)
	return {"status": "sent", "to": recipients}


def _send_whatsapp(config, doc, context, node):
	message = render_template(config.get("message") or "", doc)
	phone = render_template(config.get("phone") or config.get("to") or "", doc)
	provider = config.get("provider") or "Twilio"
	credential = config.get("credential")

	if not phone:
		frappe.throw(_("WhatsApp phone number is required on the flow node."))
	if not message:
		frappe.throw(_("WhatsApp message is required on the flow node."))

	result = send_whatsapp_message(phone, message, provider=provider, credential_name=credential)
	return {"status": "sent", **result}


def _create_task(config, doc, context, node):
	doctype = config.get("task_doctype") or "ToDo"
	due_days = int(config.get("due_days") or 3)
	payload = {
		"doctype": doctype,
		"description": render_template(config.get("description") or _("Follow up"), doc),
		"allocated_to": render_template(config.get("assigned_to") or "", doc) or None,
		"date": add_to_date(today(), days=due_days),
		"reference_type": doc.doctype,
		"reference_name": doc.name,
		"priority": config.get("priority") or "Medium",
	}
	if doctype == "Task":
		payload["subject"] = render_template(config.get("subject") or payload["description"], doc)
	new_doc = frappe.get_doc(payload)
	new_doc.insert(ignore_permissions=True)
	return {"name": new_doc.name, "doctype": doctype}


def _assign_user(config, doc, context, node):
	user = render_template(config.get("user") or config.get("assigned_to") or "", doc)
	if user:
		frappe.desk.form.assign_to.add(
			{"doctype": doc.doctype, "name": doc.name, "assign_to": [user]}
		)
	return {"assigned_to": user}


def _webhook(config, doc, context, node):
	url = config.get("url")
	if not url:
		frappe.throw(_("Webhook URL is required."))
	payload = config.get("payload") or {}
	if isinstance(payload, str):
		payload = json.loads(render_template(payload, doc))
	else:
		payload = {k: render_template(str(v), doc) for k, v in payload.items()}
	headers = config.get("headers") or {}
	resp = requests.post(url, json=payload, headers=headers, timeout=30)
	return {"status_code": resp.status_code, "body": resp.text[:500]}


def _api_call(config, doc, context, node):
	method = (config.get("method") or "POST").upper()
	url = render_template(config.get("url") or "", doc)
	headers = config.get("headers") or {}
	body = config.get("body")
	if isinstance(body, str):
		body = render_template(body, doc)
	resp = requests.request(method, url, headers=headers, data=body, timeout=30)
	return {"status_code": resp.status_code}


def _create_document(config, doc, context, node):
	target = config.get("target_doctype")
	if not target:
		frappe.throw(_("Target DocType required."))
	field_map = config.get("field_map") or {}
	payload = {"doctype": target}
	for target_field, source_expr in field_map.items():
		payload[target_field] = render_template(source_expr, doc) if "{{" in str(source_expr) else source_expr
	new_doc = frappe.get_doc(payload)
	new_doc.insert(ignore_permissions=True)
	return {"name": new_doc.name}


def _update_document(config, doc, context, node):
	updates = config.get("updates") or {}
	for field, value in updates.items():
		rendered = render_template(str(value), doc) if "{{" in str(value) else value
		doc.set(field, rendered)
	doc.flags.in_ff_flow = True
	doc.save(ignore_permissions=True)
	return {"updated": list(updates.keys())}


def _create_comment(config, doc, context, node):
	text = render_template(config.get("comment") or "", doc)
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"content": text,
		}
	).insert(ignore_permissions=True)
	return {"comment": text}


def _notification(config, doc, context, node):
	user = render_template(config.get("user") or doc.get("owner"), doc)
	subject = render_template(config.get("subject") or _("Flow notification"), doc)
	message = render_template(config.get("message") or "", doc)
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"subject": subject,
			"email_content": message,
			"for_user": user,
			"type": "Alert",
			"document_type": doc.doctype,
			"document_name": doc.name,
		}
	).insert(ignore_permissions=True)
	return {"user": user}


def _schedule_delay(config, doc, context, node):
	amount = int(config.get("amount") or 1)
	unit = (config.get("unit") or "days").lower()
	kwargs = {"days": 0, "hours": 0, "minutes": 0}
	if unit.startswith("min"):
		kwargs["minutes"] = amount
	elif unit.startswith("hour"):
		kwargs["hours"] = amount
	elif unit.startswith("week"):
		kwargs["days"] = amount * 7
	else:
		kwargs["days"] = amount
	run_at = add_to_date(now_datetime(), **kwargs)
	return {"run_at": run_at, "delay": True, "resume_node_id": node.get("next_node_id")}


def _approval_action(config, doc, context, node):
	if "dynamic_workflow_builder" in frappe.get_installed_apps():
		from dynamic_workflow_builder.engine.processor import create_approval_request
		from dynamic_workflow_builder.engine.evaluator import find_matching_rule

		rule_name = config.get("approval_rule")
		if rule_name:
			rule = frappe.get_doc("DWB Approval Rule", rule_name)
			return create_approval_request(doc, rule)
	return {"status": "skipped", "reason": "Approval engine not configured"}


def _ai_action(config, doc, context, node):
	"""Stub for AI node — integrate with ai_bot app if available."""
	action = config.get("ai_action") or "summarize"
	prompt = render_template(config.get("prompt") or "", doc)
	if "ai_bot" in frappe.get_installed_apps():
		try:
			result = frappe.call("ai_bot.api.generate_text", prompt=prompt)
			return {"result": result}
		except Exception:
			pass
	return {"status": "stub", "action": action, "prompt": prompt[:200]}
