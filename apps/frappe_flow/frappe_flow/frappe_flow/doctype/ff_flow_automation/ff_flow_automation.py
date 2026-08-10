# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document


class FFFlowAutomation(Document):
	def validate(self):
		if self.is_active and self.status == "Draft":
			self.status = "Active"
		if not self.is_active:
			self.status = "Disabled"

	def before_save(self):
		if self.status == "Active":
			self.is_active = 1
