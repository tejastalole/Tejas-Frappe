# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.utils import today


@frappe.whitelist()
def get_dashboard_stats():
	_ensure_access()
	today_date = today()
	return {
		"pending": frappe.db.count("DWB Approval Request", {"status": ["in", ["Pending", "Escalated", "Delegated"]]}),
		"approved_today": frappe.db.count(
			"DWB Approval Log", {"action": "Approved", "timestamp": [">=", today_date]}
		),
		"rejected_today": frappe.db.count(
			"DWB Approval Log", {"action": "Rejected", "timestamp": [">=", today_date]}
		),
		"escalated": frappe.db.count("DWB Approval Request", {"status": "Escalated"}),
		"overdue": frappe.db.count("DWB Approval Request", {"sla_status": "Breached", "status": "Pending"}),
	}


@frappe.whitelist()
def get_my_pending():
	user = frappe.session.user
	return frappe.get_all(
		"DWB Approval Request",
		filters={"assigned_to": user, "status": ["in", ["Pending", "Escalated", "Delegated"]]},
		fields=[
			"name",
			"reference_doctype",
			"reference_name",
			"current_level",
			"status",
			"due_date",
			"sla_status",
			"approval_rule",
		],
		order_by="due_date asc",
		limit=50,
	)


@frappe.whitelist()
def get_document_approval(doctype, docname):
	return frappe.db.get_value(
		"DWB Approval Request",
		{
			"reference_doctype": doctype,
			"reference_name": docname,
			"status": ["in", ["Pending", "Escalated", "Delegated"]],
		},
		["name", "assigned_to", "current_level", "status", "due_date", "sla_status"],
		as_dict=True,
	)


@frappe.whitelist()
def save_workflow_graph(rule_name, workflow_graph):
	frappe.only_for(("Approval Manager", "System Manager"))
	frappe.db.set_value("DWB Approval Rule", rule_name, "workflow_graph", workflow_graph)
	return {"message": _("Workflow saved.")}


@frappe.whitelist()
def get_workflow_graph(rule_name):
	frappe.only_for(("Approval Manager", "System Manager", "Approver"))
	return frappe.db.get_value("DWB Approval Rule", rule_name, "workflow_graph")


def _ensure_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.AuthenticationError)
