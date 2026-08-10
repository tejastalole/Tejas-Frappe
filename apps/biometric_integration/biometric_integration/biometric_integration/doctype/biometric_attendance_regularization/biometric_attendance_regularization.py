# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from biometric_integration.attendance_state import EVENT_DOCTYPES
from biometric_integration.regularization import apply_regularization


class BiometricAttendanceRegularization(Document):
	def validate(self):
		if self.event_category == "Check In Out" and self.log_type not in {"Check In", "Check Out"}:
			frappe.throw("Invalid log type for Check In Out regularization.")
		if self.event_category in {"Lunch Break", "Tea Break"} and self.log_type not in {"Break Start", "Break End"}:
			frappe.throw("Invalid log type for break regularization.")

	def on_submit(self):
		self.attendance_event_doctype = EVENT_DOCTYPES[self.event_category]
		apply_regularization(self)
		self.status = "Applied"

	def on_cancel(self):
		self.status = "Cancelled"
