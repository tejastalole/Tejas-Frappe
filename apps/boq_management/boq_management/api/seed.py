# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


@frappe.whitelist()
def run_seed():
	from boq_management.install import after_install

	after_install()
	return {
		"categories": frappe.db.count("BOQ Category"),
		"sub_categories": frappe.db.count("BOQ Sub Category"),
		"items": frappe.db.count("BOQ Item Master"),
	}
