# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Create typed attendance events from biometric punches with state validation."""

from __future__ import annotations

import frappe
from frappe.utils import getdate, get_datetime

from biometric_integration.attendance_summary import (
	build_break_end_fields,
	build_break_start_fields,
	build_check_in_out_fields,
	lock_attendance_day,
	refresh_attendance_day_summary,
)
from biometric_integration.attendance_state import (
	EVENT_DOCTYPES,
	AttendanceValidationError,
	DuplicatePunchError,
	EventCategory,
	get_event_link_field,
	get_office_policy,
	is_duplicate_punch,
	load_day_context,
	log_debug,
	resolve_event_type,
	validate_punch,
)


def create_attendance_event(
	punch_log_name: str,
	employee: str,
	user_id: str,
	punch_time,
	punch_status: str | None,
	device_name: str | None,
	serial_number: str | None,
	source: str,
	create_employee_checkin: bool,
	is_regularized: bool = False,
) -> dict[str, str] | None:
	"""Create attendance event after state validation. Returns {name, category} or None."""
	punch_time = get_datetime(punch_time)
	attendance_date = getdate(punch_time)
	policy = get_office_policy()

	lock_attendance_day(employee, attendance_date)
	ctx = load_day_context(employee, punch_time)
	category, log_type = resolve_event_type(employee, punch_status, punch_time, ctx=ctx)

	log_debug(
		"Resolved punch",
		{
			"employee": employee,
			"punch_log": punch_log_name,
			"category": category,
			"log_type": log_type,
			"state": ctx.current_state(),
			"punch_status": punch_status,
			"is_regularized": is_regularized,
		},
	)

	if not is_regularized:
		if is_duplicate_punch(ctx, category, log_type, punch_time):
			frappe.throw(
				"Duplicate biometric punch ignored within tolerance window.",
				exc=DuplicatePunchError,
				title="Duplicate Punch",
			)
		validate_punch(ctx, category, log_type, punch_time, skip_time_window=is_regularized)

	doctype = EVENT_DOCTYPES[category]
	if frappe.db.exists(doctype, {"employee": employee, "time": punch_time, "log_type": log_type}):
		return None

	device = device_name if device_name and frappe.db.exists("Biometric Device", device_name) else None
	doc_fields = {
		"doctype": doctype,
		"employee": employee,
		"user_id": user_id,
		"time": punch_time,
		"log_type": log_type,
		"device": device,
		"serial_number": serial_number or "",
		"source": source,
		"biometric_punch_log": punch_log_name,
		"is_regularized": 1 if is_regularized else 0,
	}

	doc_fields.update(_extra_event_fields(ctx, category, log_type, punch_time, policy))
	doc = frappe.get_doc(doc_fields)

	if category == "Check In Out" and create_employee_checkin and log_type in {"Check In", "Check Out"}:
		checkin_name = _create_employee_checkin(
			employee=employee,
			punch_time=punch_time,
			log_type=log_type,
			serial_number=serial_number,
			device_name=device_name,
		)
		if checkin_name:
			doc.employee_checkin = checkin_name

	frappe.flags.in_biometric_event_insert = True
	try:
		doc.insert(ignore_permissions=True)
	finally:
		frappe.flags.in_biometric_event_insert = False
	refresh_attendance_day_summary(employee, attendance_date)
	return {"name": doc.name, "category": category}


def _extra_event_fields(ctx, category: EventCategory, log_type: str, punch_time, policy: dict):
	if category == "Check In Out":
		return build_check_in_out_fields(ctx, log_type, punch_time)

	if log_type == "Break Start":
		minutes = (
			policy["lunch_break_duration_minutes"]
			if category == "Lunch Break"
			else policy["tea_break_duration_minutes"]
		)
		return build_break_start_fields(punch_time, minutes)

	active = ctx.active_lunch_start if category == "Lunch Break" else ctx.active_tea_start
	if not active:
		frappe.throw("Active break start not found.", exc=AttendanceValidationError)

	expected = (
		policy["lunch_break_duration_minutes"]
		if category == "Lunch Break"
		else policy["tea_break_duration_minutes"]
	)
	return build_break_end_fields(active.time, punch_time, expected, active.name)


def _create_employee_checkin(
	employee: str,
	punch_time,
	log_type: str,
	serial_number: str | None,
	device_name: str | None,
) -> str | None:
	if not frappe.db.exists("DocType", "Employee Checkin"):
		return None

	if frappe.db.exists("Employee Checkin", {"employee": employee, "time": punch_time}):
		return frappe.db.get_value("Employee Checkin", {"employee": employee, "time": punch_time}, "name")

	hrms_log_type = "IN" if log_type == "Check In" else "OUT" if log_type == "Check Out" else None
	checkin = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": punch_time,
			"device_id": serial_number or device_name,
			"log_type": hrms_log_type,
		}
	)
	checkin.insert(ignore_permissions=True)
	return checkin.name
