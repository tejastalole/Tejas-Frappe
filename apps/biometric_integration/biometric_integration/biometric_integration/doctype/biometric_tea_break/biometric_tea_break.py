# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from biometric_integration.attendance_validation import validate_event_before_insert, after_event_insert


class BiometricTeaBreak(Document):
	def before_insert(self):
		validate_event_before_insert(self)

	def on_update(self):
		after_event_insert(self)
