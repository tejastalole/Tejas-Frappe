# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.model.document import Document


class DWBApprovalRule(Document):
	def validate(self):
		self.validate_levels()
		self.sort_levels()

	def validate_levels(self):
		if not self.levels:
			frappe.throw(_("Add at least one approval level."))

		levels = [row.level for row in self.levels if row.level]
		if len(levels) != len(set(levels)):
			frappe.throw(_("Approval levels must be unique."))

	def sort_levels(self):
		self.levels.sort(key=lambda row: row.level or 0)
