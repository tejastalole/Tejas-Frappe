# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class BOQ(Document):
	def validate(self):
		if not self.boq_date:
			self.boq_date = today()
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company")

		settings = frappe.get_cached_doc("BOQ Settings", "BOQ Settings")
		if settings.enable_project_mandatory and not self.project:
			frappe.throw(_("Project is mandatory for project-based BOQ."))

		self._apply_default_costing(settings)
		self.calculate_totals()

	def _apply_default_costing(self, settings):
		if self.overhead_percent in (None, "") and settings.default_overhead_percent is not None:
			self.overhead_percent = settings.default_overhead_percent
		if self.contractor_profit_percent in (None, "") and settings.default_contractor_profit_percent is not None:
			self.contractor_profit_percent = settings.default_contractor_profit_percent
		if not self.final_rate_uom and settings.default_final_rate_uom:
			self.final_rate_uom = settings.default_final_rate_uom

	def calculate_totals(self):
		sub_total = 0
		for idx, row in enumerate(self.items, start=1):
			row.sr = idx
			row.amount = flt(row.qty) * flt(row.rate)
			sub_total += flt(row.amount)

		self.sub_total = sub_total
		overhead_pct = flt(self.overhead_percent)
		profit_pct = flt(self.contractor_profit_percent)
		self.overhead_amount = sub_total * overhead_pct / 100
		self.contractor_profit_amount = sub_total * profit_pct / 100
		self.final_rate = sub_total + flt(self.overhead_amount) + flt(self.contractor_profit_amount)
		self.total_cost = self.final_rate

	def on_submit(self):
		self.db_set("status", "Submitted")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def on_update_after_submit(self):
		self.calculate_totals()


@frappe.whitelist()
def load_category_template(boq_category: str):
	"""Load BOQ Item Master rows for a category as template lines."""
	if not boq_category:
		return []

	return frappe.get_all(
		"BOQ Item Master",
		filters={"boq_category": boq_category, "is_active": 1},
		fields=[
			"boq_category",
			"boq_sub_category",
			"name as boq_item_master",
			"item_name as item_description",
			"specification",
			"default_uom as uom",
			"default_rate as rate",
		],
		order_by="boq_sub_category asc, item_name asc",
	)


@frappe.whitelist()
def load_rate_buildup_template():
	"""Load per-m² rate buildup template (Standing Seam style)."""
	return [
		{
			"item_description": "Standing Seam Aluminium Sheet (0.9 mm)",
			"uom": "m2",
			"qty": 1,
			"rate": 1450,
		},
		{
			"item_description": "Thermal Insulation (50 mm Glass Wool)",
			"uom": "m2",
			"qty": 1,
			"rate": 320,
		},
		{
			"item_description": "Vapour Barrier",
			"uom": "m2",
			"qty": 1,
			"rate": 55,
		},
		{
			"item_description": "Clips & Fasteners",
			"uom": "Set",
			"qty": 1,
			"rate": 180,
		},
		{
			"item_description": "Sealant & Accessories",
			"uom": "LS",
			"qty": 1,
			"rate": 45,
		},
		{
			"item_description": "Labour (Installation)",
			"uom": "m2",
			"qty": 1,
			"rate": 350,
		},
		{
			"item_description": "Equipment (Lifting, Tools, Machines)",
			"uom": "m2",
			"qty": 1,
			"rate": 120,
		},
	]
