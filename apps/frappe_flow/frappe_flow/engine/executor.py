# Copyright (c) 2026, Tejas and contributors
# MIT License

import json
import time

import frappe
from frappe.utils import now_datetime

from frappe_flow.engine.actions import run_action
from frappe_flow.engine.conditions import evaluate_condition_group, _node_by_id, _next_nodes

SKIP_DOCTYPES = {
	"FF Flow Automation",
	"FF Flow Execution",
	"FF Flow Template",
	"FF Flow Webhook",
	"FF Flow Credential",
	"FF Flow Schedule",
	"FF Flow Delay Queue",
	"Error Log",
	"Activity Log",
	"Version",
	"Comment",
	"Notification Log",
}

EVENT_MAP = {
	"after_insert": "after_insert",
	"on_update": "on_update",
	"on_submit": "on_submit",
	"on_cancel": "on_cancel",
}


def handle_doc_event(doc, method=None):
	if frappe.flags.in_import or frappe.flags.in_patch:
		return
	if doc.doctype in SKIP_DOCTYPES:
		return
	if getattr(doc.flags, "in_ff_flow", False):
		return

	event = EVENT_MAP.get(method)
	if not event:
		return

	flows = frappe.get_all(
		"FF Flow Automation",
		filters={
			"is_active": 1,
			"status": "Active",
			"trigger_type": "Document Event",
			"document_type": doc.doctype,
			"trigger_event": event,
		},
		pluck="name",
	)
	for flow_name in flows:
		try:
			execute_flow(flow_name, doc=doc)
		except Exception:
			frappe.log_error(title=f"Frappe Flow failed: {flow_name}")


def execute_flow(flow_name, doc=None, context=None, resume_node_id=None, execution_name=None):
	start = time.time()
	flow = frappe.get_doc("FF Flow Automation", flow_name)
	graph = _parse_json(flow.flow_json) or {"nodes": [], "edges": []}
	nodes = graph.get("nodes") or []
	edges = graph.get("edges") or []

	if not execution_name:
		execution = frappe.get_doc(
			{
				"doctype": "FF Flow Execution",
				"flow": flow.name,
				"status": "Running",
				"triggered_on": now_datetime(),
				"reference_doctype": doc.doctype if doc else None,
				"reference_name": doc.name if doc else None,
			}
		)
		execution.insert(ignore_permissions=True)
		execution_name = execution.name
	else:
		execution = frappe.get_doc("FF Flow Execution", execution_name)

	context = context or {}
	context["flow"] = flow.name
	context["execution"] = execution_name

	try:
		start_id = resume_node_id or _find_start_node(nodes)
		_walk_flow(start_id, nodes, edges, doc, context)
		execution.status = "Success"
	except Exception as e:
		execution.status = "Failed"
		execution.error_log = frappe.get_traceback()
		raise
	finally:
		execution.execution_time = round(time.time() - start, 3)
		execution.save(ignore_permissions=True)

	return execution_name


def _walk_flow(node_id, nodes, edges, doc, context):
	pending = [node_id]
	visited = set()

	while pending:
		current = pending.pop(0)
		if current in visited:
			continue
		visited.add(current)

		node = _node_by_id(nodes, current)
		if not node:
			continue

		ntype = node.get("type")
		if ntype == "trigger":
			pass
		elif ntype == "condition":
			if doc and not evaluate_condition_group(doc, nodes, edges, current, context):
				continue
		elif ntype in ("action", "send_email", "send_whatsapp", "create_task", "assign_user", "webhook", "api_call", "create_document", "update_document", "create_comment", "notification", "approval", "ai"):
			action_node = dict(node)
			if ntype != "action":
				action_node["action_type"] = ntype
			next_ids = _next_nodes(edges, current)
			if next_ids:
				action_node["next_node_id"] = next_ids[0]
			result = run_action(action_node, doc, context)
			if result and result.get("delay"):
				_queue_delay(action_node, doc, context, result, execution_name=context.get("execution"))
				continue
		elif ntype == "delay":
			next_ids = _next_nodes(edges, current)
			config = node.get("config") or {}
			config["next_node_id"] = next_ids[0] if next_ids else None
			delay_node = {"type": "delay", "action_type": "delay", "config": config, "next_node_id": next_ids[0] if next_ids else None}
			result = run_action(delay_node, doc, context)
			if result and result.get("delay"):
				_queue_delay(delay_node, doc, context, result, execution_name=context.get("execution"))
				continue

		for nxt in _next_nodes(edges, current):
			if nxt not in visited:
				pending.append(nxt)


def _queue_delay(node, doc, context, result, execution_name):
	frappe.get_doc(
		{
			"doctype": "FF Flow Delay Queue",
			"flow": context.get("flow"),
			"execution": execution_name,
			"resume_node_id": result.get("resume_node_id") or node.get("next_node_id"),
			"reference_doctype": doc.doctype if doc else None,
			"reference_name": doc.name if doc else None,
			"run_at": result.get("run_at"),
			"status": "Pending",
			"context_json": context,
		}
	).insert(ignore_permissions=True)


def _find_start_node(nodes):
	for node in nodes:
		if node.get("type") == "trigger":
			return node.get("id")
	return nodes[0].get("id") if nodes else None


def _parse_json(value):
	if not value:
		return None
	if isinstance(value, dict):
		return value
	if isinstance(value, str):
		try:
			return json.loads(value)
		except json.JSONDecodeError:
			return None
	return value


@frappe.whitelist()
def execute(flow_name, doctype=None, docname=None):
	frappe.only_for(("Flow Admin", "Flow Designer", "System Manager"))
	doc = frappe.get_doc(doctype, docname) if doctype and docname else None
	return execute_flow(flow_name, doc=doc)
