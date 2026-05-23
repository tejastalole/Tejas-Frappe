# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
	columns = [
		{"label": _("Member ID"), "fieldname": "name", "fieldtype": "Link", "options": "Gym Member", "width": 120},
		{"label": _("Member Name"), "fieldname": "member_name", "fieldtype": "Data", "width": 180},
		{"label": _("Mobile"), "fieldname": "mobile_no", "fieldtype": "Data", "width": 120},
		{"label": _("Plan"), "fieldname": "membership_plan", "fieldtype": "Link", "options": "Membership Plan", "width": 140},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 100},
		{"label": _("Trainer"), "fieldname": "assigned_trainer", "fieldtype": "Link", "options": "Gym Trainer", "width": 140},
	]

	data = frappe.db.sql(
		"""
		SELECT
			m.name,
			m.member_name,
			m.mobile_no,
			m.assigned_trainer,
			ms.membership_plan,
			ms.end_date
		FROM `tabGym Member` m
		LEFT JOIN `tabGym Membership` ms ON ms.gym_member = m.name
			AND ms.status = 'Active'
			AND ms.end_date >= %(today)s
		WHERE m.status = 'Active'
		ORDER BY m.member_name
		""",
		{"today": today()},
		as_dict=True,
	)

	return columns, data
