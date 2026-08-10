# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WhatsAppSettings(Document):
	def validate(self):
		if self.enabled and not self.phone_number_id:
			frappe.throw("Phone Number ID is required when WhatsApp Integration is enabled.")
		if self.enabled and not self.get_password("access_token"):
			frappe.throw("Access Token is required when WhatsApp Integration is enabled.")
