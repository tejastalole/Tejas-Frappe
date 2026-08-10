import frappe


def after_install():
	if not frappe.db.exists("Role", "Bulk Data Manager"):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Bulk Data Manager",
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)
