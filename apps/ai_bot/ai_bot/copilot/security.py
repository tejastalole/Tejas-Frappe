# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Permission checks, audit logging, and safe workflow guards."""

import frappe
from frappe import _


def has_read(doctype: str) -> bool:
	return bool(doctype and frappe.has_permission(doctype, "read"))


def has_write(doctype: str) -> bool:
	return bool(doctype and frappe.has_permission(doctype, "write"))


def has_create(doctype: str) -> bool:
	return bool(doctype and frappe.has_permission(doctype, "create"))


def has_submit(doctype: str) -> bool:
	return bool(doctype and frappe.has_permission(doctype, "submit"))


def has_cancel(doctype: str) -> bool:
	return bool(doctype and frappe.has_permission(doctype, "cancel"))


def check_doctype_exists(doctype: str) -> bool:
	if not doctype:
		return False
	return bool(frappe.db.exists("DocType", doctype))


def log_action(action: str, doctype: str | None = None, name: str | None = None, detail: str = ""):
	"""Log copilot actions when enabled in AI Bot Settings."""
	try:
		settings = frappe.get_single("AI Bot Settings")
		if not getattr(settings, "log_actions", True):
			return
	except Exception:
		pass

	frappe.logger("ai_bot").info(
		"AI Bot | user={0} | action={1} | {2} {3} | {4}".format(
			frappe.session.user,
			action,
			doctype or "",
			name or "",
			detail[:200],
		)
	)


def permission_denied_message(doctype: str, perm: str = "read") -> str:
	return _("You do not have permission to {0} {1}.").format(perm, doctype)


def require_confirmation(intent: dict) -> bool:
	"""Destructive actions may need explicit confirmation in settings."""
	if intent.get("action") not in ("delete", "cancel"):
		return False
	try:
		settings = frappe.get_single("AI Bot Settings")
		return bool(getattr(settings, "confirm_destructive_actions", 1))
	except Exception:
		return intent.get("action") == "delete"
