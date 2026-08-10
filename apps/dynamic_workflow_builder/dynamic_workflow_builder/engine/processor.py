# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from dynamic_workflow_builder.engine.assignment import apply_delegation, resolve_approver
from dynamic_workflow_builder.engine.notifications import create_approval_log, notify_approver
from dynamic_workflow_builder.engine.sla import compute_due_date, refresh_sla_for_request, update_sla_status


SKIP_DOCTYPES = {
	"DWB Approval Rule",
	"DWB Approval Request",
	"DWB Approval Delegation",
	"DWB Approval Log",
	"DWB Approval Condition",
	"DWB Approval Level",
	"Error Log",
	"Activity Log",
	"Version",
	"Comment",
}


EVENT_MAP = {
	"after_insert": "Save",
	"on_update": "Update",
	"on_submit": "Submit",
	"on_update_after_submit": "Update",
}


def handle_document_event(doc, method=None):
	if frappe.flags.in_import or frappe.flags.in_patch:
		return
	if doc.doctype in SKIP_DOCTYPES:
		return
	if getattr(doc.flags, "in_dwb_approval", False):
		return

	event = EVENT_MAP.get(method)
	if not event:
		return

	from dynamic_workflow_builder.engine.evaluator import find_matching_rule

	rule = find_matching_rule(doc.doctype, doc)
	if not rule:
		return
	if rule.trigger_on != event:
		return

	if frappe.db.exists(
		"DWB Approval Request",
		{
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"status": ["in", ["Pending", "Escalated", "Delegated"]],
		},
	):
		return

	create_approval_request(doc, rule)


def create_approval_request(doc, rule):
	levels = sorted(rule.levels, key=lambda row: row.level or 0)
	if not levels:
		return

	first_level = levels[0]
	approver = apply_delegation(resolve_approver(first_level, doc))
	if not approver:
		frappe.msgprint(frappe._("Could not resolve approver for level {0}").format(first_level.level))
		return

	request = frappe.get_doc(
		{
			"doctype": "DWB Approval Request",
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"approval_rule": rule.name,
			"current_level": first_level.level,
			"status": "Pending",
			"assigned_to": approver,
			"assigned_on": now_datetime(),
			"due_date": compute_due_date(first_level.sla_hours),
			"requested_by": frappe.session.user,
			"sla_status": "Within SLA",
		}
	)
	request.insert(ignore_permissions=True)

	create_approval_log(
		approval_request=request.name,
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		user=frappe.session.user,
		action="Assigned",
		comments=f"Assigned to {approver} at level {first_level.level}",
	)
	notify_approver(request)

	return request.name


def get_level_row(rule_name: str, level: int):
	rule = frappe.get_doc("DWB Approval Rule", rule_name)
	for row in rule.levels:
		if int(row.level) == int(level):
			return row
	return None


def get_next_level(rule_name: str, current_level: int):
	rule = frappe.get_doc("DWB Approval Rule", rule_name)
	levels = sorted([int(row.level) for row in rule.levels if row.level])
	for level in levels:
		if level > int(current_level):
			return level
	return None


@frappe.whitelist()
def approve_request(name, comments=None):
	return _process_action(name, "Approved", comments=comments, advance=True)


@frappe.whitelist()
def reject_request(name, comments=None):
	return _process_action(name, "Rejected", comments=comments, advance=False)


@frappe.whitelist()
def delegate_request(name, delegate_to, comments=None):
	request = frappe.get_doc("DWB Approval Request", name)
	_ensure_can_act(request)
	delegate_to = apply_delegation(delegate_to)
	request.assigned_to = delegate_to
	request.status = "Delegated"
	request.assigned_on = now_datetime()
	request.comments = comments
	level_row = get_level_row(request.approval_rule, request.current_level)
	if level_row:
		request.due_date = compute_due_date(level_row.sla_hours)
	request.sla_status = update_sla_status(request)
	request.save(ignore_permissions=True)
	create_approval_log(
		approval_request=request.name,
		reference_doctype=request.reference_doctype,
		reference_name=request.reference_name,
		action="Delegated",
		comments=comments or delegate_to,
	)
	request.status = "Pending"
	request.save(ignore_permissions=True)
	notify_approver(request)
	return {"message": frappe._("Delegated successfully.")}


@frappe.whitelist()
def request_changes(name, comments=None):
	return _process_action(name, "Request Changes", comments=comments, advance=False, status="Pending")


def _ensure_can_act(request):
	if request.status not in ("Pending", "Escalated", "Delegated"):
		frappe.throw(frappe._("This approval request is already {0}.").format(request.status))
	if request.assigned_to != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(frappe._("You are not assigned to approve this request."), frappe.PermissionError)


def _process_action(name, action, comments=None, advance=False, status=None):
	request = frappe.get_doc("DWB Approval Request", name)
	_ensure_can_act(request)

	if advance:
		next_level = get_next_level(request.approval_rule, request.current_level)
		if next_level:
			doc = frappe.get_doc(request.reference_doctype, request.reference_name)
			level_row = get_level_row(request.approval_rule, next_level)
			approver = apply_delegation(resolve_approver(level_row, doc))
			request.current_level = next_level
			request.assigned_to = approver
			request.assigned_on = now_datetime()
			request.due_date = compute_due_date(level_row.sla_hours)
			request.status = "Pending"
			request.sla_status = "Within SLA"
			request.save(ignore_permissions=True)
			create_approval_log(
				approval_request=request.name,
				reference_doctype=request.reference_doctype,
				reference_name=request.reference_name,
				action="Approved",
				comments=comments or f"Advanced to level {next_level}",
			)
			notify_approver(request)
			return {"message": frappe._("Approved and forwarded to next level.")}

	request.status = status or action
	request.comments = comments
	request.sla_status = update_sla_status(request)
	request.save(ignore_permissions=True)
	create_approval_log(
		approval_request=request.name,
		reference_doctype=request.reference_doctype,
		reference_name=request.reference_name,
		action=action,
		comments=comments,
	)

	return {"message": frappe._("{0} successfully.").format(action)}


def get_pending_for_document(doctype, docname):
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
