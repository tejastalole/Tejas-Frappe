# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 110,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Date"),
			"fieldname": "attendance_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Status"),
			"fieldname": "final_status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Check In"),
			"fieldname": "check_in_time",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Check Out"),
			"fieldname": "check_out_time",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Late"),
			"fieldname": "late_display",
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"label": _("Lunch"),
			"fieldname": "lunch_display",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Tea"),
			"fieldname": "tea_display",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Net Hours"),
			"fieldname": "net_hours",
			"fieldtype": "Float",
			"width": 95,
			"precision": 2,
		},
		{
			"label": _("OT (min)"),
			"fieldname": "overtime_minutes",
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"label": _("State"),
			"fieldname": "current_state",
			"fieldtype": "Data",
			"width": 110,
		},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	from_date = getdate(filters.from_date)
	to_date = getdate(filters.to_date)
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date"))

	conditions = ["attendance_date BETWEEN %(from_date)s AND %(to_date)s"]
	values: dict[str, Any] = {"from_date": from_date, "to_date": to_date}

	if filters.get("employee"):
		conditions.append("employee = %(employee)s")
		values["employee"] = filters.employee

	if filters.get("company"):
		conditions.append("company = %(company)s")
		values["company"] = filters.company

	if filters.get("status"):
		conditions.append("final_status = %(status)s")
		values["status"] = filters.status

	if filters.get("late_only"):
		conditions.append("IFNULL(late_entry, 0) = 1")

	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT
			name,
			employee,
			attendance_date,
			current_state,
			final_status,
			company,
			check_in,
			check_out,
			late_entry,
			late_minutes,
			early_exit,
			early_exit_minutes,
			overtime_minutes,
			lunch_start,
			lunch_end,
			lunch_break_status,
			tea_start,
			tea_end,
			tea_break_status,
			net_working_minutes
		FROM `tabBiometric Attendance Day`
		WHERE {where}
		ORDER BY attendance_date DESC, employee ASC
		""",
		values,
		as_dict=True,
	)

	employee_names = _employee_names({row.employee for row in rows})
	data = []
	for row in rows:
		late_minutes = int(row.late_minutes or 0)
		net_minutes = int(row.net_working_minutes or 0)
		data.append(
			{
				"name": row.name,
				"employee": row.employee,
				"employee_name": employee_names.get(row.employee) or row.employee,
				"attendance_date": row.attendance_date,
				"final_status": row.final_status or "In Progress",
				"current_state": _pretty_state(row.current_state),
				"check_in_time": _fmt_clock(row.check_in),
				"check_out_time": _fmt_clock(row.check_out),
				"late_display": _fmt_late(late_minutes, row.late_entry),
				"late_minutes": late_minutes,
				"late_entry": int(row.late_entry or 0),
				"lunch_display": _fmt_break(row.lunch_start, row.lunch_end, row.lunch_break_status),
				"tea_display": _fmt_break(row.tea_start, row.tea_end, row.tea_break_status),
				"net_hours": round(net_minutes / 60.0, 2) if net_minutes else 0,
				"overtime_minutes": int(row.overtime_minutes or 0),
				"company": row.company,
			}
		)
	return data


def get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	counts: dict[str, int] = defaultdict(int)
	for row in data:
		counts[row.get("final_status") or "In Progress"] += 1

	order = ["Completed", "In Progress", "Incomplete", "Not Started"]
	labels = [status for status in order if status in counts] + [
		status for status in counts if status not in order
	]
	values = [counts[label] for label in labels]
	colors = {
		"Completed": "#16a34a",
		"In Progress": "#2563eb",
		"Incomplete": "#ea580c",
		"Not Started": "#94a3b8",
	}

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Days"), "values": values}],
		},
		"type": "donut",
		"colors": [colors.get(label, "#64748b") for label in labels],
		"height": 260,
	}


def get_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	completed = sum(1 for row in data if row.get("final_status") == "Completed")
	late = sum(1 for row in data if row.get("late_entry"))
	avg_net = (
		round(sum(row.get("net_hours") or 0 for row in data) / len(data), 2) if data else 0
	)
	total_ot = sum(int(row.get("overtime_minutes") or 0) for row in data)

	return [
		{
			"value": len(data),
			"indicator": "Blue",
			"label": _("Attendance Days"),
			"datatype": "Int",
		},
		{
			"value": completed,
			"indicator": "Green",
			"label": _("Completed"),
			"datatype": "Int",
		},
		{
			"value": late,
			"indicator": "Orange" if late else "Green",
			"label": _("Late Entries"),
			"datatype": "Int",
		},
		{
			"value": avg_net,
			"indicator": "Blue",
			"label": _("Avg Net Hours"),
			"datatype": "Float",
		},
		{
			"value": total_ot,
			"indicator": "Green" if total_ot else "Grey",
			"label": _("Total OT (min)"),
			"datatype": "Int",
		},
	]


def _employee_names(employees: set[str]) -> dict[str, str]:
	if not employees:
		return {}
	rows = frappe.get_all(
		"Employee",
		filters={"name": ("in", list(employees))},
		fields=["name", "employee_name"],
	)
	return {row.name: row.employee_name for row in rows}


def _fmt_clock(value) -> str:
	if not value:
		return "—"
	return frappe.utils.format_datetime(value, "HH:mm")


def _fmt_late(late_minutes: int, late_entry) -> str:
	if late_entry and late_minutes > 0:
		return f"+{late_minutes}m"
	if late_entry:
		return "Late"
	return "On time"


def _fmt_break(start, end, status) -> str:
	if not start and not end:
		return "—"
	left = _fmt_clock(start)
	right = _fmt_clock(end)
	tag = f" · {status}" if status and status != "Normal" else ""
	return f"{left} → {right}{tag}"


def _pretty_state(state: str | None) -> str:
	mapping = {
		"NOT_STARTED": "Not Started",
		"WORKING": "Working",
		"LUNCH_BREAK": "Lunch",
		"TEA_BREAK": "Tea",
		"COMPLETED": "Completed",
		"INCOMPLETE": "Incomplete",
	}
	return mapping.get(state or "", state or "—")
