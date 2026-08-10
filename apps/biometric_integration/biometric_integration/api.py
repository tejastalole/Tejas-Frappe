# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Whitelisted desk APIs."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from biometric_integration.regularization import create_regularization
from biometric_integration.attendance_summary import refresh_attendance_day_summary
from biometric_integration.zk_pull import pull_all_enabled, pull_device as _pull_device, test_connection


@frappe.whitelist()
def pull_now() -> dict[str, Any]:
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	settings = frappe.get_single("Biometric Settings")
	if not settings.enabled:
		frappe.throw(_("Biometric Integration is disabled in Settings."))
	return pull_all_enabled()


@frappe.whitelist()
def pull_device(device: str) -> dict[str, Any]:
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	return _pull_device(device)


@frappe.whitelist()
def test_device_connection(device: str) -> dict[str, Any]:
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	return test_connection(device)


@frappe.whitelist()
def get_attendance_day_summary(employee: str, attendance_date: str) -> dict[str, Any]:
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	summary = refresh_attendance_day_summary(employee, attendance_date)
	name = frappe.db.get_value(
		"Biometric Attendance Day",
		{"employee": employee, "attendance_date": attendance_date},
		"name",
	)
	return {"name": name, "summary": summary}


@frappe.whitelist()
def regularize_attendance(
	employee: str,
	attendance_date: str,
	event_category: str,
	log_type: str,
	corrected_time: str,
	reason: str,
	punch_log: str | None = None,
) -> dict[str, Any]:
	return create_regularization(
		employee=employee,
		attendance_date=attendance_date,
		event_category=event_category,
		log_type=log_type,
		corrected_time=corrected_time,
		reason=reason,
		punch_log=punch_log,
	)
