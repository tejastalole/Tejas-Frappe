# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

import frappe


def after_install():
	if not frappe.db.exists("ZKTeco Settings", "ZKTeco Settings"):
		doc = frappe.get_doc({"doctype": "ZKTeco Settings"})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
