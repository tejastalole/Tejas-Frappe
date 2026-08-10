# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.model.document import Document


class BOQItemMaster(Document):
	def validate(self):
		if self.boq_sub_category:
			category = frappe.db.get_value("BOQ Sub Category", self.boq_sub_category, "boq_category")
			if category and self.boq_category and category != self.boq_category:
				frappe.throw(_("Sub Category does not belong to the selected Category."))
