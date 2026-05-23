# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class TejasTesting(Document):
	def before_save(self):
		if not self.naming_series:
			self.naming_series = "TEJ-.YYYY.-"
		self.full_name = self._build_full_name()

	def _build_full_name(self) -> str:
		parts = [self.first_name, self.middle_name, self.last_name]
		return " ".join(part.strip() for part in parts if part and part.strip())
