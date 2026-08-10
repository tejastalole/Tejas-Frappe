# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from dynamic_workflow_builder.engine.assignment import apply_delegation, resolve_approver
from dynamic_workflow_builder.engine.notifications import create_approval_log, notify_approver
from dynamic_workflow_builder.engine.processor import get_level_row, get_next_level
from dynamic_workflow_builder.engine.sla import compute_due_date, refresh_sla_for_request


def run_escalation_check():
	pending = frappe.get_all(
		"DWB Approval Request",
		filters={"status": ["in", ["Pending", "Escalated", "Delegated"]]},
		fields=["name"],
	)
	for row in pending:
		try:
			process_request_escalation(row.name)
		except Exception:
			frappe.log_error(title=f"DWB Escalation failed for {row.name}")


def process_request_escalation(request_name: str):
	request = frappe.get_doc("DWB Approval Request", request_name)
	sla_status = refresh_sla_for_request(request_name)
	if sla_status != "Breached":
		return

	level_row = get_level_row(request.approval_rule, request.current_level)
	if not level_row:
		return

	action = level_row.escalation_action or "Notify"
	hours_overdue = _hours_overdue(request.due_date)

	if action == "Notify":
		notify_approver(
			request,
			subject=frappe._("SLA breached: {0} {1}").format(request.reference_doctype, request.reference_name),
			message=frappe._("Approval SLA has been breached. Please take action."),
		)
		request.status = "Escalated"
		request.save(ignore_permissions=True)
		create_approval_log(
			approval_request=request.name,
			reference_doctype=request.reference_doctype,
			reference_name=request.reference_name,
			action="Escalated",
			comments="SLA breached - notified approver",
		)
		return

	if action == "Escalate Next" or (action == "Notify" and hours_overdue >= 24):
		next_level = get_next_level(request.approval_rule, request.current_level)
		if next_level:
			doc = frappe.get_doc(request.reference_doctype, request.reference_name)
			next_row = get_level_row(request.approval_rule, next_level)
			approver = apply_delegation(resolve_approver(next_row, doc))
			request.current_level = next_level
			request.assigned_to = approver
			request.assigned_on = now_datetime()
			request.due_date = compute_due_date(next_row.sla_hours)
			request.status = "Pending"
			request.sla_status = "Within SLA"
			request.save(ignore_permissions=True)
			create_approval_log(
				approval_request=request.name,
				reference_doctype=request.reference_doctype,
				reference_name=request.reference_name,
				action="Escalated",
				comments=f"Escalated to level {next_level}",
			)
			notify_approver(request)
			return

	if action == "Escalate Admin" or hours_overdue >= 24:
		admins = frappe.get_all("Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent")
		if admins:
			request.assigned_to = admins[0]
			request.status = "Escalated"
			request.assigned_on = now_datetime()
			request.due_date = add_to_date(now_datetime(), hours=24)
			request.save(ignore_permissions=True)
			notify_approver(request)
		return

	if action == "Auto Reject" or hours_overdue >= 48:
		request.status = "Rejected"
		request.rejection_reason = "Auto rejected due to SLA breach"
		request.save(ignore_permissions=True)
		create_approval_log(
			approval_request=request.name,
			reference_doctype=request.reference_doctype,
			reference_name=request.reference_name,
			action="Rejected",
			comments="Auto rejected after SLA breach",
		)


def _hours_overdue(due_date):
	if not due_date:
		return 0
	return max(0, (get_datetime(now_datetime()) - get_datetime(due_date)).total_seconds() / 3600)
