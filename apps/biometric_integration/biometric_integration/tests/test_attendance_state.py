# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from biometric_integration.attendance_events import create_attendance_event
from biometric_integration.attendance_state import (
	AttendanceValidationError,
	DuplicatePunchError,
	load_day_context,
)
from biometric_integration.attendance_summary import calculate_day_summary, refresh_attendance_day_summary


class TestAttendanceState(FrappeTestCase):
	def setUp(self):
		self.employee = self._ensure_employee()
		self.day = "2026-08-10"
		self._clear_day(self.employee, self.day)

	def test_normal_day_flow(self):
		self._punch("0", f"{self.day} 09:02:00")
		self._punch("2", f"{self.day} 13:00:00")
		self._punch("3", f"{self.day} 13:45:00")
		self._punch("4", f"{self.day} 16:00:00")
		self._punch("5", f"{self.day} 16:15:00")
		self._punch("1", f"{self.day} 18:03:00")

		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["current_state"], "COMPLETED")
		self.assertEqual(summary["final_status"], "Completed")
		self.assertEqual(summary["late_minutes"], 2)
		self.assertEqual(summary["overtime_minutes"], 3)
		self.assertEqual(summary["lunch_actual_duration_minutes"], 45)
		self.assertEqual(summary["tea_actual_duration_minutes"], 15)
		self.assertEqual(summary["lunch_excess_duration_minutes"], 0)
		self.assertEqual(frappe.db.count("Biometric Check In Check Out", {"employee": self.employee}), 2)
		self.assertEqual(frappe.db.count("Biometric Lunch Break", {"employee": self.employee}), 2)
		self.assertEqual(frappe.db.count("Biometric Tea Break", {"employee": self.employee}), 2)

	def test_duplicate_check_in_rejected(self):
		self._punch("0", f"{self.day} 09:02:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("0", f"{self.day} 09:03:00")

	def test_duplicate_punch_tolerance(self):
		self._punch("0", f"{self.day} 09:02:00")
		with self.assertRaises(DuplicatePunchError):
			self._punch("0", f"{self.day} 09:02:01")

	def test_lunch_over_duration(self):
		self._punch("0", f"{self.day} 09:00:00")
		self._punch("2", f"{self.day} 13:00:00")
		self._punch("3", f"{self.day} 13:52:00")
		summary = calculate_day_summary(load_day_context(self.employee, f"{self.day} 13:52:00"))
		self.assertEqual(summary["lunch_actual_duration_minutes"], 52)
		self.assertEqual(summary["lunch_excess_duration_minutes"], 7)
		self.assertEqual(summary["lunch_break_status"], "Over Break")

	def test_lunch_outside_window_rejected(self):
		self._punch("0", f"{self.day} 09:00:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("2", f"{self.day} 11:30:00")

	def test_tea_outside_window_rejected(self):
		self._punch("0", f"{self.day} 09:00:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("4", f"{self.day} 15:30:00")

	def test_checkout_blocked_during_lunch(self):
		self._punch("0", f"{self.day} 09:00:00")
		self._punch("2", f"{self.day} 13:00:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("1", f"{self.day} 18:00:00")

	def test_early_checkout(self):
		self._punch("0", f"{self.day} 09:00:00")
		self._punch("1", f"{self.day} 17:45:00")
		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["early_exit"], 1)
		self.assertEqual(summary["early_exit_minutes"], 15)

	def _punch(self, status: str, punch_time: str):
		log = frappe.get_doc(
			{
				"doctype": "Biometric Punch Log",
				"user_id": "1001",
				"employee": self.employee,
				"punch_time": punch_time,
				"punch_status": status,
				"source": "ADMS",
				"processing_status": "Pending",
			}
		).insert(ignore_permissions=True)
		return create_attendance_event(
			punch_log_name=log.name,
			employee=self.employee,
			user_id="1001",
			punch_time=punch_time,
			punch_status=status,
			device_name=None,
			serial_number=None,
			source="ADMS",
			create_employee_checkin=False,
		)

	def _ensure_employee(self) -> str:
		name = frappe.db.get_value("Employee", {"attendance_device_id": "1001"}, "name")
		if name:
			frappe.db.set_value("Employee", name, "attendance_device_id", "1001")
			return name
		company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
			"Company", {}, "name"
		)
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Rahul",
				"last_name": "Patil",
				"employee_name": "Rahul Patil",
				"company": company,
				"status": "Active",
				"date_of_joining": "2026-01-01",
				"date_of_birth": "1990-01-01",
				"gender": "Male",
				"attendance_device_id": "1001",
			}
		).insert(ignore_permissions=True)
		return doc.name

	def _clear_day(self, employee: str, day: str):
		for doctype in (
			"Biometric Check In Check Out",
			"Biometric Lunch Break",
			"Biometric Tea Break",
			"Biometric Punch Log",
			"Biometric Attendance Day",
		):
			for name in frappe.get_all(doctype, filters={"employee": employee}, pluck="name"):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		frappe.db.delete(
			"Biometric Attendance Day",
			{"employee": employee, "attendance_date": day},
		)
		frappe.db.commit()
