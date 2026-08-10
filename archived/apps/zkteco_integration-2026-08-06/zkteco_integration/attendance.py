# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Create Employee Checkin records from parsed ADMS punches."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import get_datetime


def process_attendance_rows(
	rows: list[dict[str, Any]],
	serial_number: str | None = None,
) -> dict[str, int]:
	"""Insert Employee Checkin for each punch. Returns counts."""
	counts = {"downloaded": len(rows), "inserted": 0, "skipped": 0, "errors": 0}

	for row in rows:
		try:
			outcome = _process_one(row, serial_number=serial_number)
			counts[outcome] += 1
		except Exception:
			counts["errors"] += 1
			frappe.log_error(title="ZKTeco Punch Error", message=frappe.get_traceback())

	return counts


def _process_one(row: dict[str, Any], serial_number: str | None) -> str:
	user_id = str(row.get("user_id") or "").strip()
	punch_time = get_datetime(row.get("punch_time"))
	if not user_id or not punch_time:
		return "skipped"

	employee = resolve_employee(user_id)
	if not employee:
		frappe.logger("zkteco_integration").warning(f"No Employee for biometric ID: {user_id}")
		return "skipped"

	if not frappe.db.exists("DocType", "Employee Checkin"):
		return "skipped"

	if frappe.db.exists("Employee Checkin", {"employee": employee, "time": punch_time}):
		return "skipped"

	frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": punch_time,
			"device_id": serial_number or "",
			"log_type": map_status_to_log_type(row.get("punch_status")),
		}
	).insert(ignore_permissions=True)

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
