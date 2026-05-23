# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document


class AIBotConversation(Document):
	def before_insert(self):
		if not self.user:
			self.user = frappe.session.user
