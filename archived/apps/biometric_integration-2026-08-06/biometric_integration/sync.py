# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Process punches into Biometric Punch Log + Employee Checkin."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import get_datetime, now_datetime


def process_attendance_rows(
	rows: list[dict[str, Any]],
	device_name: str | None = None,
	serial_number: str | None = None,
	source: str = "ADMS",
) -> dict[str, int]:
	"""Insert punch logs and optionally Employee Checkin. Returns counts."""
	settings = frappe.get_single("Biometric Settings")
	counts = {"downloaded": len(rows), "inserted": 0, "skipped": 0, "errors": 0}

	for row in rows:
		try:
			outcome = _process_one(
				row,
				device_name=device_name,
				serial_number=serial_number,
				source=source,
				create_checkin=bool(settings.create_employee_checkin),
			)
			counts[outcome] += 1
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
	create_checkin: bool,
) -> str:
	user_id = str(row.get("user_id") or "").strip()
	punch_time = get_datetime(row.get("punch_time"))
	if not user_id or not punch_time:
		return "skipped"

	serial = serial_number or ""
	if frappe.db.exists(
		"Biometric Punch Log",
		{"user_id": user_id, "punch_time": punch_time, "serial_number": serial},
	):
		return "skipped"

	employee = resolve_employee(user_id)

	doc = frappe.get_doc(
		{
			"doctype": "Biometric Punch Log",
			"user_id": user_id,
			"employee": employee,
			"punch_time": punch_time,
			"punch_status": row.get("punch_status") or "",
			"verify_mode": row.get("verify_mode") or "",
			"device": device_name if device_name and frappe.db.exists("Biometric Device", device_name) else None,
			"serial_number": serial,
			"source": source,
			"processed": 0,
			"raw_line": row.get("raw_line") or "",
		}
	)
	doc.insert(ignore_permissions=True)

	if not create_checkin:
		return "inserted"

	if not employee:
		return "inserted"

	if not frappe.db.exists("DocType", "Employee Checkin"):
		return "inserted"

	if frappe.db.exists("Employee Checkin", {"employee": employee, "time": punch_time}):
		doc.processed = 1
		doc.save(ignore_permissions=True)
		return "skipped"

	checkin = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": punch_time,
			"device_id": serial or device_name,
			"log_type": map_status_to_log_type(row.get("punch_status")),
		}
	)
	checkin.insert(ignore_permissions=True)

	doc.processed = 1
	doc.employee_checkin = checkin.name
	doc.save(ignore_permissions=True)
	return "inserted"


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
	if status is None or status == "":
		return None
	value = str(status).strip().upper()
	if value in {"0", "I", "IN", "CHECKIN", "C/IN"}:
		return "IN"
	if value in {"1", "O", "OUT", "CHECKOUT", "C/OUT"}:
		return "OUT"
	return None
