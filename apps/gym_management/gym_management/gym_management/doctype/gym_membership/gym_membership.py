# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today


class GymMembership(Document):
	def validate(self):
		self.set_end_date_and_amount()
		self.update_status_from_dates()

	def set_end_date_and_amount(self):
		if not self.membership_plan or not self.start_date:
			return

		plan = frappe.get_cached_doc("Membership Plan", self.membership_plan)
		if plan.duration_days:
			self.end_date = add_days(self.start_date, plan.duration_days)

		if not self.amount and plan.fee:
			self.amount = plan.fee

	def update_status_from_dates(self):
		if self.status == "Cancelled" or not self.end_date:
			return

		if getdate(self.end_date) < getdate(today()):
			self.status = "Expired"
