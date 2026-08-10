# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


def execute(filters=None):
	filters = filters or {}
	conditions = {"sla_status": "Breached"}
	if filters.get("from_date"):
		conditions["due_date"] = [">=", filters.from_date]
	if filters.get("to_date"):
		conditions["due_date"] = ["<=", filters.to_date]

	columns = [
		{"label": "Request", "fieldname": "name", "fieldtype": "Link", "options": "DWB Approval Request", "width": 140},
		{"label": "DocType", "fieldname": "reference_doctype", "fieldtype": "Data", "width": 120},
		{"label": "Document", "fieldname": "reference_name", "fieldtype": "Data", "width": 120},
		{"label": "Assigned To", "fieldname": "assigned_to", "fieldtype": "Link", "options": "User", "width": 120},
		{"label": "Due Date", "fieldname": "due_date", "fieldtype": "Datetime", "width": 150},
		{"label": "SLA Status", "fieldname": "sla_status", "fieldtype": "Data", "width": 110},
	]

	data = frappe.get_all(
		"DWB Approval Request",
		filters=conditions,
		fields=["name", "reference_doctype", "reference_name", "assigned_to", "due_date", "sla_status"],
		order_by="due_date desc",
	)
	return columns, data
