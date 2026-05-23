# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


def after_install():
	frappe.clear_cache()
	if not frappe.db.exists("AI Bot Settings", "AI Bot Settings"):
		doc = frappe.get_doc({"doctype": "AI Bot Settings", "log_actions": 1})
		doc.insert(ignore_permissions=True)
