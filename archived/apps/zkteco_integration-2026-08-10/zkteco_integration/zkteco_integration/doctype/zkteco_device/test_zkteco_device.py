# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from zkteco_integration.utils.checkin import create_employee_checkin
from zkteco_integration.utils.mapping import map_punch_to_log_type, next_log_type


class TestZKTecoMapping(FrappeTestCase):
	def test_map_punch_states(self):
		self.assertEqual(map_punch_to_log_type("0"), "IN")
		self.assertEqual(map_punch_to_log_type("1"), "OUT")
		self.assertIsNone(map_punch_to_log_type("9"))


class TestZKTecoCheckin(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Employee", {"name": ("like", "HR-EMP-%")}):
			self.skipTest("No Employee fixture")

	def test_duplicate_prevention(self):
		emp = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not emp:
			self.skipTest("No active employee")
		ts = "2099-01-01 09:00:00"
		device = "TEST-DEVICE-DUP"
		r1 = create_employee_checkin(employee=emp, timestamp=ts, log_type="IN", device_id=device)
		r2 = create_employee_checkin(employee=emp, timestamp=ts, log_type="IN", device_id=device)
		self.assertEqual(r1["status"], "success")
		self.assertEqual(r2["status"], "duplicate")
		frappe.db.delete("Employee Checkin", {"employee": emp, "time": ts, "device_id": device})
		frappe.db.commit()
