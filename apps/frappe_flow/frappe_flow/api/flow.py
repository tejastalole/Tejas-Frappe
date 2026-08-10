# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _

from frappe_flow.engine.executor import execute_flow


@frappe.whitelist(allow_guest=True)
def webhook(endpoint_path=None, **kwargs):
	if not endpoint_path:
		frappe.throw(_("Invalid webhook."), frappe.PermissionError)

	hook = frappe.db.get_value(
		"FF Flow Webhook",
		{"endpoint_path": endpoint_path, "is_active": 1},
		["name", "flow", "secret_key"],
		as_dict=True,
	)
	if not hook:
		frappe.throw(_("Webhook not found."), frappe.NotFound)

	secret = frappe.get_doc("FF Flow Webhook", hook.name).get_password("secret_key")
	provided = frappe.get_request_header("X-Flow-Secret") or kwargs.get("secret")
	if secret and provided != secret:
		frappe.throw(_("Invalid secret."), frappe.PermissionError)

	try:
		execute_flow(hook.flow, context={"webhook_payload": kwargs})
	except Exception:
		frappe.log_error(title=f"Webhook flow failed: {hook.flow}")
		frappe.throw(_("Flow execution failed."))

	return {"status": "ok"}


@frappe.whitelist()
def get_dashboard_stats():
	frappe.only_for(("Flow Admin", "Flow Designer", "Flow User", "System Manager"))
	total = frappe.db.count("FF Flow Automation")
	active = frappe.db.count("FF Flow Automation", {"status": "Active"})
	success = frappe.db.count("FF Flow Execution", {"status": "Success"})
	failed = frappe.db.count("FF Flow Execution", {"status": "Failed"})
	running = frappe.db.count("FF Flow Execution", {"status": "Running"})
	total_exec = success + failed + running
	rate = round((success / total_exec) * 100, 1) if total_exec else 0
	return {
		"active_flows": active,
		"total_flows": total,
		"failed_flows": failed,
		"success_rate": rate,
		"execution_count": total_exec,
	}


@frappe.whitelist()
def save_flow_graph(flow_name, flow_json):
	frappe.only_for(("Flow Admin", "Flow Designer", "System Manager"))
	frappe.db.set_value("FF Flow Automation", flow_name, "flow_json", flow_json)
	return {"message": _("Flow saved.")}


@frappe.whitelist()
def get_flow_graph(flow_name):
	frappe.only_for(("Flow Admin", "Flow Designer", "System Manager"))
	return frappe.db.get_value("FF Flow Automation", flow_name, ["flow_json", "flow_name", "document_type", "trigger_event", "trigger_type"], as_dict=True)


@frappe.whitelist()
def test_whatsapp(phone, message, credential, provider=None):
	"""Send a test WhatsApp message using FF Flow Credential."""
	frappe.only_for(("Flow Admin", "Flow Designer", "System Manager"))
	from frappe_flow.engine.whatsapp import send_whatsapp_message

	return send_whatsapp_message(phone, message, provider=provider, credential_name=credential)


@frappe.whitelist()
def install_template(template_name, new_flow_name=None):
	frappe.only_for(("Flow Admin", "Flow Designer", "System Manager"))
	template = frappe.get_doc("FF Flow Template", template_name)
	flow = frappe.get_doc(
		{
			"doctype": "FF Flow Automation",
			"flow_name": new_flow_name or template.template_name,
			"category": template.category,
			"description": template.description,
			"flow_json": template.flow_json,
			"status": "Draft",
			"is_active": 0,
			"trigger_type": "Document Event",
		}
	)
	flow.insert()
	return {"name": flow.name, "message": _("Template installed.")}


@frappe.whitelist()
def ai_generate_flow(prompt):
	"""Generate a basic flow graph from natural language (rule-based stub)."""
	frappe.only_for(("Flow Admin", "Flow Designer", "System Manager"))
	prompt_l = (prompt or "").lower()
	doctype = "Quotation"
	if "lead" in prompt_l:
		doctype = "Lead"
	elif "sales order" in prompt_l:
		doctype = "Sales Order"

	nodes = [
		{"id": "trigger", "type": "trigger", "label": f"{doctype} Submitted", "x": 80, "y": 60},
	]
	edges = []
	y = 160

	if "100000" in prompt_l or "1 lakh" in prompt_l or " lakh" in prompt_l:
		nodes.append(
			{
				"id": "cond-1",
				"type": "condition",
				"label": "grand_total > 100000",
				"x": 80,
				"y": y,
				"config": {"field_name": "grand_total", "operator": ">", "value": "100000"},
			}
		)
		edges.append({"source": "trigger", "target": "cond-1"})
		prev = "cond-1"
		y += 100
	else:
		prev = "trigger"

	if "whatsapp" in prompt_l:
		nid = "act-wa"
		nodes.append({"id": nid, "type": "send_whatsapp", "label": "Send WhatsApp", "x": 80, "y": y, "config": {"message": "Hello {{doc.customer_name}}"}})
		edges.append({"source": prev, "target": nid})
		prev = nid
		y += 100

	if "email" in prompt_l:
		nid = "act-email"
		nodes.append({"id": nid, "type": "send_email", "label": "Send Email", "x": 80, "y": y, "config": {"to": "{{doc.owner}}", "subject": "Approval needed", "message": "Please review {{doc.name}}"}})
		edges.append({"source": prev, "target": nid})
		prev = nid
		y += 100

	if "follow" in prompt_l or "task" in prompt_l:
		nid = "act-task"
		nodes.append({"id": nid, "type": "create_task", "label": "Create Follow-up", "x": 80, "y": y, "config": {"due_days": 3, "description": "Follow up on {{doc.name}}"}})
		edges.append({"source": prev, "target": nid})
		prev = nid
		y += 100

	if "day" in prompt_l:
		import re

		match = re.search(r"(\d+)\s*day", prompt_l)
		days = int(match.group(1)) if match else 3
		nid = "delay-1"
		nodes.append({"id": nid, "type": "delay", "label": f"Wait {days} days", "x": 80, "y": y, "config": {"amount": days, "unit": "days"}})
		edges.append({"source": prev, "target": nid})
		prev = nid
		y += 100

	nodes.append({"id": "end", "type": "end", "label": "Complete", "x": 80, "y": y})
	edges.append({"source": prev, "target": "end"})

	return {
		"flow_json": {"nodes": nodes, "edges": edges},
		"document_type": doctype,
		"trigger_event": "on_submit",
		"trigger_type": "Document Event",
	}
