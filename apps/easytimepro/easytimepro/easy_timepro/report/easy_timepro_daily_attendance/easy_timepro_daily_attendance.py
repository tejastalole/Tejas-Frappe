# Copyright (c) 2026, Tejas and contributors
# MIT License

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import format_datetime, formatdate, get_datetime, getdate, time_diff_in_hours


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	message = get_message(filters, data)
	return columns, data, message, chart, summary


def get_message(filters: frappe._dict, data: list[dict]) -> str:
	from_date = formatdate(filters.from_date) if filters.from_date else ""
	to_date = formatdate(filters.to_date) if filters.to_date else ""
	return f"""
	<div class="etp-report-banner">
		<div class="etp-report-banner__title">{_("Easy TimePro Daily Attendance")}</div>
		<div class="etp-report-banner__meta">
			{_('Period')}: <b>{from_date}</b> → <b>{to_date}</b>
			&nbsp;·&nbsp; {_('Records')}: <b>{len(data)}</b>
		</div>
	</div>
	"""


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Date"),
			"fieldname": "attendance_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 200,
		},
		{
			"label": _("Employee ID"),
			"fieldname": "emp_code",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Check In"),
			"fieldname": "first_in",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Check Out"),
			"fieldname": "last_out",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Work Hours"),
			"fieldname": "work_hours",
			"fieldtype": "Float",
			"width": 150,
			"precision": 2,
		},
		{
			"label": _("Status"),
			"fieldname": "day_status",
			"fieldtype": "Data",
			"width": 150,
		},
	]


def get_data(filters: frappe._dict) -> list[dict]:
	from_date = getdate(filters.from_date) if filters.from_date else getdate()
	to_date = getdate(filters.to_date) if filters.to_date else getdate()

	conditions = ["punch_time >= %(from_dt)s", "punch_time < %(to_dt)s"]
	params = {
		"from_dt": f"{from_date} 00:00:00",
		"to_dt": f"{frappe.utils.add_days(to_date, 1)} 00:00:00",
	}

	if filters.employee:
		conditions.append("employee = %(employee)s")
		params["employee"] = filters.employee
	if filters.emp_code:
		conditions.append("emp_code = %(emp_code)s")
		params["emp_code"] = filters.emp_code

	where = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		select
			name, emp_code, employee, employee_name, punch_time, log_type
		from `tabEasy TimePro Punch Log`
		where {where}
		order by punch_time asc
		""",
		params,
		as_dict=True,
	)

	grouped: dict[tuple, list] = defaultdict(list)
	for row in rows:
		day = getdate(row.punch_time)
		key = (day, row.employee or "", row.emp_code or "")
		grouped[key].append(row)

	employee_ids = {row.employee for row in rows if row.employee}
	employee_meta = {}
	if employee_ids:
		for emp in frappe.get_all(
			"Employee",
			filters={"name": ("in", list(employee_ids))},
			fields=["name", "employee_name", "department"],
		):
			employee_meta[emp.name] = emp

	data = []
	for (day, employee, emp_code), punches in sorted(
		grouped.items(), key=lambda x: (x[0][0], x[0][2]), reverse=True
	):
		ins = [p for p in punches if p.log_type == "IN"]
		outs = [p for p in punches if p.log_type == "OUT"]
		first_in = ins[0].punch_time if ins else None
		last_out = outs[-1].punch_time if outs else None

		work_hours = 0.0
		if first_in and last_out and get_datetime(last_out) > get_datetime(first_in):
			work_hours = max(0.0, time_diff_in_hours(last_out, first_in))

		if first_in and last_out:
			status = "Complete"
		elif first_in:
			status = "Checked In"
		elif last_out:
			status = "Checked Out"
		else:
			status = "No IN/OUT"

		meta = employee_meta.get(employee) or frappe._dict()
		employee_name = punches[0].employee_name or meta.employee_name or ""

		data.append(
			{
				"attendance_date": day,
				"emp_code": emp_code,
				"employee": employee or None,
				"employee_name": employee_name,
				"department": meta.department or "",
				"first_in": format_datetime(first_in, "HH:mm") if first_in else "—",
				"last_out": format_datetime(last_out, "HH:mm") if last_out else "—",
				"in_count": len(ins),
				"out_count": len(outs),
				"total_punches": len(punches),
				"work_hours": round(work_hours, 2),
				"day_status": status,
			}
		)

	return data


def get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	by_date: dict = defaultdict(lambda: {"in": 0, "out": 0, "hours": 0.0})
	for row in data:
		key = formatdate(row["attendance_date"], "dd MMM")
		by_date[key]["in"] += row["in_count"]
		by_date[key]["out"] += row["out_count"]
		by_date[key]["hours"] += row["work_hours"]

	# preserve chronological order from sorted dates
	ordered = []
	seen = set()
	for row in sorted(data, key=lambda r: r["attendance_date"]):
		label = formatdate(row["attendance_date"], "dd MMM")
		if label not in seen:
			seen.add(label)
			ordered.append(label)
	labels = ordered[-14:]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Check In"), "values": [by_date[d]["in"] for d in labels]},
				{"name": _("Check Out"), "values": [by_date[d]["out"] for d in labels]},
			],
		},
		"type": "line",
		"lineOptions": {"regionFill": 1, "hideDots": 0, "heatline": 0},
		"axisOptions": {"xIsSeries": 1},
		"colors": ["#1f4b99", "#b42318"],
		"height": 280,
	}


def get_summary(data: list[dict]) -> list[dict]:
	employees = {r["employee"] or r["emp_code"] for r in data}
	complete = sum(1 for r in data if r["day_status"] == "Complete")
	checked_in = sum(1 for r in data if r["day_status"] == "Checked In")
	total_punches = sum(r["total_punches"] for r in data)
	avg_hours = (
		round(sum(r["work_hours"] for r in data if r["work_hours"]) / max(1, complete), 2)
		if complete
		else 0
	)

	return [
		{"value": len(data), "label": _("Attendance Days"), "datatype": "Int"},
		{"value": len(employees), "label": _("Employees"), "datatype": "Int"},
		{"value": complete, "label": _("Complete Days"), "datatype": "Int", "indicator": "Green"},
		{"value": checked_in, "label": _("Still Checked In"), "datatype": "Int", "indicator": "Blue"},
		{"value": total_punches, "label": _("Total Punches"), "datatype": "Int"},
		{"value": avg_hours, "label": _("Avg Work Hours"), "datatype": "Float", "indicator": "Orange"},
	]
