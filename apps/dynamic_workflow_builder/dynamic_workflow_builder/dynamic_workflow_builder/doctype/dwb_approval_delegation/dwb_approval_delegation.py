# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class DWBApprovalDelegation(Document):
	def validate(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date."))
		if self.user == self.delegate_to:
			frappe.throw(_("User and Delegate To must be different."))

	def before_save(self):
		if getdate(self.from_date) <= getdate(today()) <= getdate(self.to_date):
			self.is_active = 1
