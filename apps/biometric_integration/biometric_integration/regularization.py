# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Admin regularization for missing biometric events."""

from __future__ import annotations

import frappe
from frappe.utils import getdate, get_datetime, now_datetime

from biometric_integration.attendance_events import create_attendance_event
from biometric_integration.attendance_state import AttendanceValidationError, EVENT_DOCTYPES


@frappe.whitelist()
def create_regularization(
	employee: str,
	attendance_date: str,
	event_category: str,
	log_type: str,
	corrected_time: str,
	reason: str,
	punch_log: str | None = None,
):
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	if not reason:
		frappe.throw("Reason is required for regularization.")

	doc = frappe.get_doc(
		{
			"doctype": "Biometric Attendance Regularization",
			"employee": employee,
			"attendance_date": getdate(attendance_date),
			"event_category": event_category,
			"log_type": log_type,
			"corrected_time": get_datetime(corrected_time),
			"reason": reason,
			"biometric_punch_log": punch_log,
			"corrected_by": frappe.session.user,
			"correction_time": now_datetime(),
			"status": "Draft",
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return {"name": doc.name, "attendance_event": doc.attendance_event}


def apply_regularization(doc) -> None:
	user_id = frappe.db.get_value("Employee", doc.employee, "attendance_device_id") or doc.employee
	frappe.flags.in_biometric_event_insert = True
	try:
		result = create_attendance_event(
			punch_log_name=doc.biometric_punch_log or doc.name,
			employee=doc.employee,
			user_id=str(user_id),
			punch_time=doc.corrected_time,
			punch_status=_status_for_event(doc.event_category, doc.log_type),
			device_name=None,
			serial_number=None,
			source="Manual",
			create_employee_checkin=False,
			is_regularized=True,
		)
	finally:
		frappe.flags.in_biometric_event_insert = False

	if not result:
		frappe.throw("Regularization did not create an attendance event.")
	doc.db_set(
		{
			"attendance_event": result["name"],
			"attendance_event_doctype": EVENT_DOCTYPES[doc.event_category],
		},
		update_modified=False,
	)


def _status_for_event(event_category: str, log_type: str) -> str:
	mapping = {
		("Check In Out", "Check In"): "0",
		("Check In Out", "Check Out"): "1",
		("Lunch Break", "Break Start"): "2",
		("Lunch Break", "Break End"): "3",
		("Tea Break", "Break Start"): "4",
		("Tea Break", "Break End"): "5",
	}
	key = (event_category, log_type)
	if key not in mapping:
		frappe.throw("Unsupported regularization event type.", exc=AttendanceValidationError)
	return mapping[key]
