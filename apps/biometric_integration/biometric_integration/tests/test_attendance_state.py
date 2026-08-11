# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from biometric_integration.attendance_events import create_attendance_event
from biometric_integration.attendance_state import (
	AttendanceValidationError,
	DuplicatePunchError,
	load_day_context,
	resolve_event_type,
)
from biometric_integration.attendance_summary import calculate_day_summary, refresh_attendance_day_summary


class TestAttendanceState(FrappeTestCase):
	def setUp(self):
		self.employee = self._ensure_employee()
		self.day = "2026-08-10"
		self._clear_day(self.employee, self.day)
		frappe.db.set_single_value("Biometric Settings", "use_time_based_punch_routing", 1)

	def test_normal_day_flow(self):
		# Status codes ignored — routing is by punch time
		self._punch("", f"{self.day} 08:55:00")
		self._punch("", f"{self.day} 13:00:00")
		self._punch("", f"{self.day} 13:45:00")
		self._punch("", f"{self.day} 16:00:00")
		self._punch("", f"{self.day} 16:15:00")
		self._punch("", f"{self.day} 19:03:00")

		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["current_state"], "COMPLETED")
		self.assertEqual(summary["final_status"], "Completed")
		self.assertEqual(summary["late_minutes"], 0)
		self.assertEqual(summary["overtime_minutes"], 3)
		self.assertEqual(summary["lunch_actual_duration_minutes"], 45)
		self.assertEqual(summary["tea_actual_duration_minutes"], 15)
		self.assertEqual(summary["lunch_excess_duration_minutes"], 0)
		self.assertEqual(frappe.db.count("Biometric Check In Check Out", {"employee": self.employee}), 2)
		self.assertEqual(frappe.db.count("Biometric Lunch Break", {"employee": self.employee}), 2)
		self.assertEqual(frappe.db.count("Biometric Tea Break", {"employee": self.employee}), 2)

	def test_time_routing_check_in_before_office_start(self):
		category, log_type = resolve_event_type(self.employee, "", f"{self.day} 08:30:00")
		self.assertEqual(category, "Check In Out")
		self.assertEqual(log_type, "Check In")

	def test_time_routing_lunch_start_and_end(self):
		self._punch("", f"{self.day} 08:50:00")
		category, log_type = resolve_event_type(self.employee, "99", f"{self.day} 12:30:00")
		self.assertEqual((category, log_type), ("Lunch Break", "Break Start"))
		self._punch("", f"{self.day} 12:30:00")
		category, log_type = resolve_event_type(self.employee, "99", f"{self.day} 13:10:00")
		self.assertEqual((category, log_type), ("Lunch Break", "Break End"))

	def test_time_routing_tea_and_checkout_after_seven(self):
		self._punch("", f"{self.day} 08:50:00")
		category, log_type = resolve_event_type(self.employee, "", f"{self.day} 16:05:00")
		self.assertEqual((category, log_type), ("Tea Break", "Break Start"))
		self._punch("", f"{self.day} 16:05:00")
		category, log_type = resolve_event_type(self.employee, "", f"{self.day} 16:20:00")
		self.assertEqual((category, log_type), ("Tea Break", "Break End"))
		self._punch("", f"{self.day} 16:20:00")
		category, log_type = resolve_event_type(self.employee, "", f"{self.day} 19:10:00")
		self.assertEqual((category, log_type), ("Check In Out", "Check Out"))

	def test_punch_between_tea_and_checkout_rejected(self):
		self._punch("", f"{self.day} 08:50:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("", f"{self.day} 18:30:00")

	def test_duplicate_check_in_rejected(self):
		self._punch("", f"{self.day} 08:50:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("", f"{self.day} 08:55:00")

	def test_duplicate_punch_tolerance(self):
		self._punch("", f"{self.day} 08:50:00")
		with self.assertRaises(DuplicatePunchError):
			self._punch("", f"{self.day} 08:50:01")

	def test_lunch_over_duration(self):
		self._punch("", f"{self.day} 08:50:00")
		self._punch("", f"{self.day} 13:00:00")
		self._punch("", f"{self.day} 13:52:00")
		summary = calculate_day_summary(load_day_context(self.employee, f"{self.day} 13:52:00"))
		self.assertEqual(summary["lunch_actual_duration_minutes"], 52)
		self.assertEqual(summary["lunch_excess_duration_minutes"], 7)
		self.assertEqual(summary["lunch_break_status"], "Over Break")

	def test_punch_between_office_and_lunch_rejected(self):
		self._punch("", f"{self.day} 08:50:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("", f"{self.day} 11:30:00")

	def test_punch_between_lunch_and_tea_rejected(self):
		self._punch("", f"{self.day} 08:50:00")
		with self.assertRaises(AttendanceValidationError):
			self._punch("", f"{self.day} 15:30:00")

	def test_checkout_blocked_during_lunch(self):
		self._punch("", f"{self.day} 08:50:00")
		self._punch("", f"{self.day} 13:00:00")
		# After 7 PM resolves to Check Out, but lunch is still active → rejected
		with self.assertRaises(AttendanceValidationError):
			self._punch("", f"{self.day} 19:05:00")

	def test_tea_allowed_while_lunch_left_open(self):
		self._punch("", f"{self.day} 08:50:00")
		self._punch("", f"{self.day} 13:00:00")  # lunch start only
		self._punch("", f"{self.day} 16:05:00")  # tea should still store
		self.assertEqual(
			frappe.db.count("Biometric Tea Break", {"employee": self.employee, "log_type": "Break Start"}),
			1,
		)

	def test_late_check_in_before_lunch_window(self):
		# 09:15 is inside 9–10 AM check-in window → not late
		self._punch("", f"{self.day} 09:15:00")
		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["late_minutes"], 0)
		self.assertEqual(summary["current_state"], "WORKING")

	def test_late_minutes_count_from_10_am(self):
		self._punch("", f"{self.day} 10:14:00")
		cio = frappe.get_all(
			"Biometric Check In Check Out",
			filters={"employee": self.employee, "log_type": "Check In"},
			fields=["late_entry", "late_minutes"],
		)[0]
		self.assertEqual(cio.late_entry, 1)
		self.assertEqual(cio.late_minutes, 14)
		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["late_minutes"], 14)

	def test_tea_without_check_in_is_stored(self):
		self._punch("", f"{self.day} 16:05:00")
		self._punch("", f"{self.day} 16:20:00")
		self.assertEqual(frappe.db.count("Biometric Tea Break", {"employee": self.employee}), 2)
		self.assertEqual(frappe.db.count("Biometric Check In Check Out", {"employee": self.employee}), 0)
		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["tea_actual_duration_minutes"], 15)

	def test_lunch_without_check_in_is_stored(self):
		self._punch("", f"{self.day} 12:30:00")
		self._punch("", f"{self.day} 13:15:00")
		self.assertEqual(frappe.db.count("Biometric Lunch Break", {"employee": self.employee}), 2)
		self.assertEqual(frappe.db.count("Biometric Check In Check Out", {"employee": self.employee}), 0)
		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["lunch_actual_duration_minutes"], 45)

	def test_checkout_without_check_in_is_stored(self):
		self._punch("", f"{self.day} 19:12:00")
		self.assertEqual(
			frappe.db.count(
				"Biometric Check In Check Out",
				{"employee": self.employee, "log_type": "Check Out"},
			),
			1,
		)
		summary = refresh_attendance_day_summary(self.employee, self.day)
		self.assertEqual(summary["current_state"], "COMPLETED")
		self.assertEqual(summary["overtime_minutes"], 12)

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
