# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document
from frappe.utils import random_string


class FFFlowWebhook(Document):
	def before_insert(self):
		if not self.endpoint_path:
			slug = frappe.scrub(self.webhook_name).replace("_", "-")
			self.endpoint_path = f"frappe_flow/webhook/{slug}"

	def validate(self):
		if not self.get_password("secret_key"):
			self.secret_key = random_string(32)
