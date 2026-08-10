# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ZKTecoEmployeeMapping(Document):
	def validate(self):
		self.zkteco_user_id = str(self.zkteco_user_id or "").strip()
		if not self.zkteco_user_id:
			frappe.throw("ZKTeco User ID is required")

		filters = {
			"zkteco_device": self.zkteco_device,
			"zkteco_user_id": self.zkteco_user_id,
			"name": ("!=", self.name),
		}
		if frappe.db.exists("ZKTeco Employee Mapping", filters):
			frappe.throw(
				f"Mapping already exists for user {self.zkteco_user_id} on device {self.zkteco_device}"
			)
