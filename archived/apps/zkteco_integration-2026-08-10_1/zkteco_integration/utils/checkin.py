# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

"""Create Employee Checkin with duplicate prevention."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import get_datetime

from zkteco_integration.utils.mapping import resolve_employee, resolve_log_type


def create_employee_checkin(
	*,
	employee: str | None = None,
	zkteco_user_id: str | None = None,
	timestamp,
	log_type: str | None = None,
	device_id: str | None = None,
	punch_status: str | None = None,
	punch: str | None = None,
) -> dict[str, Any]:
	"""
	Create Employee Checkin or return duplicate.

	Duplicate key: employee + time + device_id
	"""
	punch_time = get_datetime(timestamp)
	if not punch_time:
		return {"status": "error", "message": "Invalid timestamp"}

	device_id = (device_id or "").strip()
	emp = (employee or "").strip() or None
	if not emp and zkteco_user_id:
		emp = resolve_employee(zkteco_user_id, device_id or None)

	if not emp:
		return {
			"status": "error",
			"message": f"No Employee mapping for ZKTeco user {zkteco_user_id or ''}",
		}

	if not frappe.db.exists("Employee", emp):
		return {"status": "error", "message": f"Invalid employee: {emp}"}

	if frappe.db.exists(
		"Employee Checkin",
		{"employee": emp, "time": punch_time, "device_id": device_id},
	):
		existing = frappe.db.get_value(
			"Employee Checkin",
			{"employee": emp, "time": punch_time, "device_id": device_id},
			"name",
		)
		return {"status": "duplicate", "name": existing}

	resolved_type = (log_type or "").strip().upper() or None
	if resolved_type not in {"IN", "OUT"}:
		resolved_type = resolve_log_type(emp, punch_time, punch_status, punch)

	doc = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": emp,
			"time": punch_time,
			"log_type": resolved_type,
			"device_id": device_id,
		}
	)
	doc.insert(ignore_permissions=True)
	return {"status": "success", "name": doc.name, "log_type": resolved_type, "employee": emp}


def bulk_create_employee_checkins(device_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
	total = len(records or [])
	created = duplicate = failed = 0
	errors: list[str] = []

	for row in records or []:
		try:
			result = create_employee_checkin(
				employee=row.get("employee"),
				zkteco_user_id=row.get("zkteco_user_id"),
				timestamp=row.get("timestamp") or row.get("time"),
				log_type=row.get("log_type"),
				device_id=device_id or row.get("device_id"),
				punch_status=row.get("punch_status"),
				punch=row.get("punch"),
			)
			status = result.get("status")
			if status == "success":
				created += 1
			elif status == "duplicate":
				duplicate += 1
			else:
				failed += 1
				errors.append(result.get("message") or "unknown")
		except Exception as exc:
			failed += 1
			errors.append(str(exc))
			frappe.log_error(title="ZKTeco Bulk Checkin Error", message=frappe.get_traceback())

	frappe.db.commit()
	return {
		"status": "success" if failed == 0 else ("partial" if created else "error"),
		"total": total,
		"created": created,
		"duplicate": duplicate,
		"failed": failed,
		"errors": errors[:20],
	}
