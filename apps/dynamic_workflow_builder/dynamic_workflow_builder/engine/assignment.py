# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import getdate, today


def resolve_approver(level_row, doc):
	approver_type = level_row.approver_type
	if approver_type == "Specific User":
		return level_row.user

	if approver_type == "Role Based":
		if not level_row.role:
			return None
		users = frappe.get_all(
			"Has Role",
			filters={"role": level_row.role, "parenttype": "User"},
			fields=["parent"],
			limit=1,
		)
		return users[0].parent if users else None

	if approver_type == "Department Head":
		department = level_row.department or doc.get("department")
		if department:
			head = frappe.db.get_value("Department", department, "parent_department")
			# fallback: employee department head via Employee
			emp = frappe.db.get_value(
				"Employee",
				{"department": department, "status": "Active"},
				"user_id",
			)
			if emp:
				return emp
		return None

	if approver_type == "Document Owner Manager":
		owner = doc.get("owner")
		employee = frappe.db.get_value("Employee", {"user_id": owner, "status": "Active"}, "reports_to")
		if employee:
			return frappe.db.get_value("Employee", employee, "user_id")
		return owner

	return None


def apply_delegation(user: str):
	if not user:
		return user

	delegation = frappe.db.get_value(
		"DWB Approval Delegation",
		{
			"user": user,
			"is_active": 1,
			"from_date": ["<=", today()],
			"to_date": [">=", today()],
		},
		"delegate_to",
	)
	return delegation or user
