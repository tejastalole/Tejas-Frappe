# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document


class BOQSubCategory(Document):
	def validate(self):
		if self.boq_category and self.sub_category_name:
			existing = frappe.db.exists(
				"BOQ Sub Category",
				{
					"boq_category": self.boq_category,
					"sub_category_name": self.sub_category_name,
					"name": ("!=", self.name),
				},
			)
			if existing:
				frappe.throw("Sub Category already exists for this Category.")
