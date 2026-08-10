# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BiometricDevice(Document):
	def validate(self):
		if self.serial_number:
			self.serial_number = self.serial_number.strip()
		if not self.tcp_port:
			self.tcp_port = 4370
