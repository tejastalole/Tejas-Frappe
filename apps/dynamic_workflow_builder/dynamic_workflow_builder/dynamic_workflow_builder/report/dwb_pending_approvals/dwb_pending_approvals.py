# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


def execute(filters=None):
	filters = filters or {}
	conditions = {}
	if filters.get("assigned_to"):
		conditions["assigned_to"] = filters.assigned_to
	if filters.get("status"):
		conditions["status"] = filters.status
	else:
		conditions["status"] = ["in", ["Pending", "Escalated", "Delegated"]]
	if filters.get("reference_doctype"):
		conditions["reference_doctype"] = filters.reference_doctype

	columns = [
		{"label": "Request", "fieldname": "name", "fieldtype": "Link", "options": "DWB Approval Request", "width": 140},
		{"label": "DocType", "fieldname": "reference_doctype", "fieldtype": "Data", "width": 120},
		{"label": "Document", "fieldname": "reference_name", "fieldtype": "Data", "width": 120},
		{"label": "Assigned To", "fieldname": "assigned_to", "fieldtype": "Link", "options": "User", "width": 120},
		{"label": "Level", "fieldname": "current_level", "fieldtype": "Int", "width": 80},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": "Due Date", "fieldname": "due_date", "fieldtype": "Datetime", "width": 150},
		{"label": "SLA Status", "fieldname": "sla_status", "fieldtype": "Data", "width": 110},
	]

	data = frappe.get_all(
		"DWB Approval Request",
		filters=conditions,
		fields=[
			"name",
			"reference_doctype",
			"reference_name",
			"assigned_to",
			"current_level",
			"status",
			"due_date",
			"sla_status",
		],
		order_by="due_date asc",
	)
	return columns, data
