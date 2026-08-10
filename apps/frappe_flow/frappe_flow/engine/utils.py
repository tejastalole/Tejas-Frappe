# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _


def resolve_email_recipients(value):
	"""Turn usernames or comma-separated addresses into valid email list."""
	if not value:
		frappe.throw(_("Email recipient is required."))

	if isinstance(value, (list, tuple)):
		parts = [str(p).strip() for p in value if p]
	else:
		parts = [p.strip() for p in str(value).replace(";", ",").split(",") if p.strip()]

	emails = []
	for part in parts:
		if "@" in part:
			emails.append(part)
			continue

		email = frappe.db.get_value("User", part, "email")
		if email:
			emails.append(email)
			continue

		frappe.throw(
			_('Recipient "{0}" is not a valid email. Open User "{0}" and set an email address.').format(part)
		)

	return emails
