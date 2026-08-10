# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Process punches into Biometric Punch Log + typed attendance events."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import getdate, now_datetime

from biometric_integration.attendance_events import create_attendance_event
from biometric_integration.attendance_state import (
	AttendanceValidationError,
	DuplicatePunchError,
	get_event_link_field,
	load_day_context,
	resolve_event_type,
)


def process_attendance_rows(
	rows: list[dict[str, Any]],
	device_name: str | None = None,
	serial_number: str | None = None,
	source: str = "ADMS",
) -> dict[str, int]:
	"""Insert punch logs and typed attendance events. Returns counts."""
	settings = frappe.get_single("Biometric Settings")
	counts = {"downloaded": len(rows), "inserted": 0, "skipped": 0, "errors": 0, "rejected": 0, "duplicate": 0}

	for row in rows:
		try:
			outcome = _process_one(
				row,
				device_name=device_name,
				serial_number=serial_number,
				source=source,
				create_events=bool(settings.create_attendance_events),
				create_employee_checkin=bool(settings.create_employee_checkin),
			)
			counts[outcome] = counts.get(outcome, 0) + 1
		except Exception:
			counts["errors"] += 1
			frappe.log_error(title="Biometric Punch Error", message=frappe.get_traceback())

	if device_name and frappe.db.exists("Biometric Device", device_name):
		frappe.db.set_value("Biometric Device", device_name, "last_sync", now_datetime())

	return counts


def _process_one(
	row: dict[str, Any],
	device_name: str | None,
	serial_number: str | None,
	source: str,
	create_events: bool,
	create_employee_checkin: bool,
) -> str:
	user_id = str(row.get("user_id") or "").strip()
	punch_time = frappe.utils.get_datetime(row.get("punch_time"))
	if not user_id or not punch_time:
		return "skipped"

	serial = serial_number or ""
	if frappe.db.exists(
		"Biometric Punch Log",
		{"user_id": user_id, "punch_time": punch_time, "serial_number": serial},
	):
		return "skipped"

	employee = resolve_employee(user_id)
	punch_status = row.get("punch_status") or ""
	event_category = None
	event_log_type = None
	if employee:
		try:
			ctx = load_day_context(employee, punch_time)
			event_category, event_log_type = resolve_event_type(
				employee, punch_status, punch_time, ctx=ctx
			)
		except AttendanceValidationError:
			pass

	doc = frappe.get_doc(
		{
			"doctype": "Biometric Punch Log",
			"user_id": user_id,
			"employee": employee,
			"punch_time": punch_time,
			"punch_status": punch_status,
			"verify_mode": row.get("verify_mode") or "",
			"device": device_name if device_name and frappe.db.exists("Biometric Device", device_name) else None,
			"serial_number": serial,
			"source": source,
			"processed": 0,
			"processing_status": "Pending",
			"attendance_date": getdate(punch_time),
			"raw_line": row.get("raw_line") or "",
			"event_category": event_category,
			"event_log_type": event_log_type,
		}
	)
	doc.insert(ignore_permissions=True)

	if not create_events or not employee:
		doc.db_set("processing_status", "Accepted" if not employee else "Pending", update_modified=False)
		return "inserted"

	try:
		result = create_attendance_event(
			punch_log_name=doc.name,
			employee=employee,
			user_id=user_id,
			punch_time=punch_time,
			punch_status=punch_status,
			device_name=device_name,
			serial_number=serial,
			source=source,
			create_employee_checkin=create_employee_checkin,
		)
	except DuplicatePunchError as exc:
		_mark_punch_log(doc, "Duplicate", str(exc), processed=1)
		return "duplicate"
	except AttendanceValidationError as exc:
		_mark_punch_log(doc, "Rejected", str(exc), processed=1)
		return "rejected"

	if result:
		event_name = result["name"]
		event_category = result["category"]
		link_field = get_event_link_field(event_category)
		doc.db_set(link_field, event_name, update_modified=False)
		checkin = (
			frappe.db.get_value("Biometric Check In Check Out", event_name, "employee_checkin")
			if event_category == "Check In Out"
			else None
		)
		doc.db_set(
			{
				"processed": 1,
				"processing_status": "Accepted",
				"employee_checkin": checkin,
				"event_category": event_category,
			},
			update_modified=True,
		)
		return "inserted"

	doc.db_set({"processed": 1, "processing_status": "Duplicate"}, update_modified=True)
	return "duplicate"


def _mark_punch_log(doc, status: str, reason: str, processed: int = 1) -> None:
	doc.db_set(
		{
			"processing_status": status,
			"rejection_reason": reason,
			"processed": processed,
		},
		update_modified=True,
	)


def resolve_employee(user_id: str) -> str | None:
	"""Map device PIN → Employee via attendance_device_id, then name / number."""
	if not user_id:
		return None

	employee = frappe.db.get_value(
		"Employee",
		{"attendance_device_id": user_id, "status": "Active"},
		"name",
	)
	if employee:
		return employee

	employee = frappe.db.get_value("Employee", {"name": user_id, "status": "Active"}, "name")
	if employee:
		return employee

	return frappe.db.get_value(
		"Employee",
		{"employee_number": user_id, "status": "Active"},
		"name",
	)


def map_status_to_log_type(status: str | None) -> str | None:
	"""Legacy helper for HRMS Employee Checkin log_type."""
	if status is None or status == "":
		return None
	value = str(status).strip().upper()
	if value in {"0", "I", "IN", "CHECKIN", "C/IN"}:
		return "IN"
	if value in {"1", "O", "OUT", "CHECKOUT", "C/OUT"}:
		return "OUT"
	return None
