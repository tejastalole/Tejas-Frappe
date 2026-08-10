# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

"""Employee mapping + IN/OUT helpers."""

from __future__ import annotations

import frappe
from frappe.utils import get_datetime, getdate


def resolve_employee(zkteco_user_id: str, device_name: str | None = None) -> str | None:
	"""Map device PIN → Employee via ZKTeco Employee Mapping, then attendance_device_id."""
	user_id = str(zkteco_user_id or "").strip()
	if not user_id:
		return None

	filters = {"zkteco_user_id": user_id, "enabled": 1}
	if device_name:
		filters["zkteco_device"] = device_name

	employee = frappe.db.get_value("ZKTeco Employee Mapping", filters, "employee")
	if employee:
		return employee

	# Fallback: any-device mapping with same user id
	if device_name:
		employee = frappe.db.get_value(
			"ZKTeco Employee Mapping",
			{"zkteco_user_id": user_id, "enabled": 1},
			"employee",
		)
		if employee:
			return employee

	return frappe.db.get_value(
		"Employee",
		{"attendance_device_id": user_id, "status": "Active"},
		"name",
	)


def map_punch_to_log_type(punch_status: str | None, punch: str | None = None) -> str | None:
	value = str(punch_status if punch_status not in (None, "") else punch or "").strip().upper()
	if value in {"0", "I", "IN", "CHECKIN", "C/IN"}:
		return "IN"
	if value in {"1", "O", "OUT", "CHECKOUT", "C/OUT"}:
		return "OUT"
	return None


def next_log_type(employee: str, punch_time) -> str:
	"""Alternate IN / OUT based on last checkin of the same day."""
	day = getdate(punch_time)
	last = frappe.db.get_value(
		"Employee Checkin",
		{
			"employee": employee,
			"time": ("between", [f"{day} 00:00:00", f"{day} 23:59:59"]),
		},
		["log_type", "time"],
		order_by="time desc",
		as_dict=True,
	)
	if not last or not last.get("log_type"):
		return "IN"
	if str(last.log_type).upper() == "IN":
		return "OUT"
	return "IN"


def resolve_log_type(
	employee: str,
	punch_time,
	punch_status: str | None = None,
	punch: str | None = None,
	auto_detect: bool | None = None,
) -> str:
	mapped = map_punch_to_log_type(punch_status, punch)
	if mapped:
		return mapped

	if auto_detect is None:
		auto_detect = bool(frappe.db.get_single_value("ZKTeco Settings", "auto_detect_inout"))

	if auto_detect and employee:
		return next_log_type(employee, get_datetime(punch_time))

	return "IN"
