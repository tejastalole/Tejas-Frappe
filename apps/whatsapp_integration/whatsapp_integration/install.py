import frappe


def after_install():
	"""Ensure WhatsApp Manager role exists after install."""
	if not frappe.db.exists("Role", "WhatsApp Manager"):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "WhatsApp Manager",
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)
