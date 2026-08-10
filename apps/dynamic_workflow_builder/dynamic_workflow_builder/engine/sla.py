# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime


def compute_due_date(sla_hours: int):
	hours = int(sla_hours or 24)
	return add_to_date(now_datetime(), hours=hours)


def update_sla_status(request_doc):
	if not request_doc.due_date or request_doc.status != "Pending":
		return request_doc.sla_status or "Within SLA"

	now = get_datetime(now_datetime())
	due = get_datetime(request_doc.due_date)
	assigned = get_datetime(request_doc.assigned_on) if request_doc.assigned_on else now
	total_seconds = (due - assigned).total_seconds() or 1
	remaining_seconds = (due - now).total_seconds()

	if remaining_seconds <= 0:
		return "Breached"
	if remaining_seconds <= total_seconds * 0.25:
		return "Near Breach"
	return "Within SLA"


def refresh_sla_for_request(request_name: str):
	status = frappe.db.get_value("DWB Approval Request", request_name, ["due_date", "assigned_on", "status"], as_dict=True)
	if not status:
		return
	doc = frappe._dict(status)
	sla_status = update_sla_status(doc)
	frappe.db.set_value("DWB Approval Request", request_name, "sla_status", sla_status, update_modified=False)
	return sla_status
