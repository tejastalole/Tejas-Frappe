# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Daily attendance summary calculations and persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe
from frappe.utils import get_datetime, getdate, time_diff_in_seconds

from biometric_integration.attendance_state import (
	AttendanceDayContext,
	AttendanceState,
	get_office_policy,
	load_day_context,
)


def get_or_create_attendance_day(employee: str, attendance_date, for_update: bool = False):
	attendance_date = getdate(attendance_date)
	name = frappe.db.get_value(
		"Biometric Attendance Day",
		{"employee": employee, "attendance_date": attendance_date},
		"name",
		for_update=for_update,
	)
	if name:
		return frappe.get_doc("Biometric Attendance Day", name)

	doc = frappe.get_doc(
		{
			"doctype": "Biometric Attendance Day",
			"employee": employee,
			"attendance_date": attendance_date,
			"current_state": "NOT_STARTED",
			"final_status": "In Progress",
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc


def lock_attendance_day(employee: str, attendance_date):
	"""Load/create day summary with row lock to reduce concurrent punch races."""
	attendance_date = getdate(attendance_date)
	frappe.db.sql(
		"""
		SELECT name FROM `tabBiometric Attendance Day`
		WHERE employee = %s AND attendance_date = %s
		FOR UPDATE
		""",
		(employee, attendance_date),
	)
	return get_or_create_attendance_day(employee, attendance_date, for_update=True)


def refresh_attendance_day_summary(employee: str, attendance_date) -> dict[str, Any]:
	ctx = load_day_context(employee, attendance_date)
	summary = calculate_day_summary(ctx)
	doc = get_or_create_attendance_day(employee, attendance_date)
	doc.update(summary)
	doc.save(ignore_permissions=True)
	return summary


def calculate_day_summary(ctx: AttendanceDayContext) -> dict[str, Any]:
	policy = get_office_policy()
	state = ctx.current_state()
	final_status = _final_status(ctx, state)

	check_in_time = ctx.check_in.time if ctx.check_in else None
	check_out_time = ctx.check_out.time if ctx.check_out else None
	lunch_start = ctx.lunch_start.time if ctx.lunch_start else None
	lunch_end = ctx.lunch_end.time if ctx.lunch_end else None
	tea_start = ctx.tea_start.time if ctx.tea_start else None
	tea_end = ctx.tea_end.time if ctx.tea_end else None

	lunch_expected = policy["lunch_break_duration_minutes"]
	tea_expected = policy["tea_break_duration_minutes"]
	lunch_actual = _minutes_between(lunch_start, lunch_end)
	tea_actual = _minutes_between(tea_start, tea_end)
	lunch_excess = max(lunch_actual - lunch_expected, 0) if lunch_end else 0
	tea_excess = max(tea_actual - tea_expected, 0) if tea_end else 0

	late_entry, late_minutes = _late_entry(check_in_time, ctx.attendance_date, policy["late_entry_after_time"])
	early_exit, early_exit_minutes = _early_exit(check_out_time, ctx.attendance_date, policy["office_end_time"])
	overtime_minutes = _overtime_minutes(check_out_time, ctx.attendance_date, policy["office_end_time"])

	total_elapsed = _minutes_between(check_in_time, check_out_time)
	total_break = lunch_actual + tea_actual
	net_working = max(total_elapsed - total_break, 0) if check_out_time else 0

	return {
		"current_state": state,
		"final_status": final_status,
		"check_in": check_in_time,
		"check_out": check_out_time,
		"lunch_start": lunch_start,
		"lunch_end": lunch_end,
		"lunch_expected_duration_minutes": lunch_expected,
		"lunch_actual_duration_minutes": lunch_actual,
		"lunch_excess_duration_minutes": lunch_excess,
		"lunch_break_status": _break_status(lunch_start, lunch_end, lunch_actual, lunch_expected),
		"tea_start": tea_start,
		"tea_end": tea_end,
		"tea_expected_duration_minutes": tea_expected,
		"tea_actual_duration_minutes": tea_actual,
		"tea_excess_duration_minutes": tea_excess,
		"tea_break_status": _break_status(tea_start, tea_end, tea_actual, tea_expected),
		"total_elapsed_minutes": total_elapsed,
		"total_break_minutes": total_break,
		"net_working_minutes": net_working,
		"late_entry": late_entry,
		"late_minutes": late_minutes,
		"early_exit": early_exit,
		"early_exit_minutes": early_exit_minutes,
		"overtime_minutes": overtime_minutes,
		"lunch_used": 1 if ctx.lunch_used else 0,
		"tea_used": 1 if ctx.tea_used else 0,
	}


def build_check_in_out_fields(
	ctx: AttendanceDayContext,
	log_type: str,
	punch_time: datetime,
) -> dict[str, Any]:
	policy = get_office_policy()
	fields: dict[str, Any] = {"attendance_date": getdate(punch_time)}
	if log_type == "Check In":
		late_entry, late_minutes = _late_entry(punch_time, getdate(punch_time), policy["late_entry_after_time"])
		fields.update({"late_entry": late_entry, "late_minutes": late_minutes})
	elif log_type == "Check Out":
		early_exit, early_exit_minutes = _early_exit(
			punch_time, getdate(punch_time), policy["office_end_time"]
		)
		fields.update(
			{
				"early_exit": early_exit,
				"early_exit_minutes": early_exit_minutes,
				"overtime_minutes": _overtime_minutes(
					punch_time, getdate(punch_time), policy["office_end_time"]
				),
			}
		)
	return fields


def build_break_start_fields(punch_time: datetime, break_minutes: int) -> dict[str, Any]:
	punch_time = get_datetime(punch_time)
	return {
		"attendance_date": getdate(punch_time),
		"expected_end_time": punch_time + timedelta(minutes=break_minutes),
		"expected_duration_minutes": break_minutes,
	}


def build_break_end_fields(
	start_time: datetime,
	end_time: datetime,
	expected_minutes: int,
	paired_event: str,
) -> dict[str, Any]:
	start_time = get_datetime(start_time)
	end_time = get_datetime(end_time)
	actual = _minutes_between(start_time, end_time)
	excess = max(actual - expected_minutes, 0)
	status = "Incomplete" if actual <= 0 else ("Over Break" if excess > 0 else "Normal")
	return {
		"attendance_date": getdate(end_time),
		"actual_duration_minutes": actual,
		"excess_duration_minutes": excess,
		"expected_duration_minutes": expected_minutes,
		"break_status": status,
		"paired_event": paired_event,
	}


def _final_status(ctx: AttendanceDayContext, state: AttendanceState) -> str:
	if state == "COMPLETED":
		return "Completed"
	if state in {"INCOMPLETE", "LUNCH_BREAK", "TEA_BREAK"}:
		return "Incomplete"
	if state == "WORKING":
		return "In Progress"
	return "Not Started"


def _break_status(start, end, actual: int, expected: int) -> str:
	if start and not end:
		return "Incomplete"
	if not start:
		return ""
	if actual > expected:
		return "Over Break"
	return "Normal"


def _minutes_between(start, end) -> int:
	if not start or not end:
		return 0
	seconds = time_diff_in_seconds(get_datetime(end), get_datetime(start))
	return max(int(seconds // 60), 0)


def _combine_date_time(attendance_date, time_value) -> datetime:
	if isinstance(time_value, str):
		time_part = time_value
	else:
		time_part = time_value.strftime("%H:%M:%S")
	return get_datetime(f"{attendance_date} {time_part}")


def _late_entry(check_in_time, attendance_date, late_after_time) -> tuple[int, int]:
	"""Late minutes start after late_after_time (default 10:00 AM), not office start (9:00 AM)."""
	if not check_in_time:
		return 0, 0
	late_after = _combine_date_time(attendance_date, late_after_time)
	check_in_time = get_datetime(check_in_time)
	if check_in_time <= late_after:
		return 0, 0
	return 1, _minutes_between(late_after, check_in_time)


def _early_exit(check_out_time, attendance_date, office_end_time) -> tuple[int, int]:
	if not check_out_time:
		return 0, 0
	office_end = _combine_date_time(attendance_date, office_end_time)
	check_out_time = get_datetime(check_out_time)
	if check_out_time >= office_end:
		return 0, 0
	return 1, _minutes_between(check_out_time, office_end)


def _overtime_minutes(check_out_time, attendance_date, office_end_time) -> int:
	if not check_out_time:
		return 0
	office_end = _combine_date_time(attendance_date, office_end_time)
	check_out_time = get_datetime(check_out_time)
	if check_out_time <= office_end:
		return 0
	return _minutes_between(office_end, check_out_time)
