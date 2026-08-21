# Copyright (c) 2026, Tejas and contributors
# MIT License

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.utils import add_days, formatdate, get_datetime, getdate, nowdate, time_diff_in_hours


@frappe.whitelist()
def get_workspace_kpis() -> dict:
	"""Live KPI payload for Easy TimePro workspace Analytics block."""
	today = getdate(nowdate())
	week_start = add_days(today, -6)

	punches = frappe.db.sql(
		"""
		select employee, emp_code, punch_time, log_type
		from `tabEasy TimePro Punch Log`
		where punch_time >= %(from_dt)s and punch_time < %(to_dt)s
		order by punch_time asc
		""",
		{
			"from_dt": f"{week_start} 00:00:00",
			"to_dt": f"{add_days(today, 1)} 00:00:00",
		},
		as_dict=True,
	)

	by_day_employee: dict[tuple, list] = defaultdict(list)
	daily_counts: dict = defaultdict(lambda: {"in": 0, "out": 0, "total": 0})

	for row in punches:
		day = getdate(row.punch_time)
		key = (day, row.employee or row.emp_code or "")
		by_day_employee[key].append(row)
		bucket = daily_counts[day]
		bucket["total"] += 1
		if row.log_type == "IN":
			bucket["in"] += 1
		elif row.log_type == "OUT":
			bucket["out"] += 1

	today_rows = [k for k in by_day_employee if k[0] == today]
	present_today = len(today_rows)

	complete_today = 0
	still_in = 0
	work_hours = []
	for key in today_rows:
		day_punches = by_day_employee[key]
		ins = [p for p in day_punches if p.log_type == "IN"]
		outs = [p for p in day_punches if p.log_type == "OUT"]
		first_in = ins[0].punch_time if ins else None
		last_out = outs[-1].punch_time if outs else None
		if first_in and last_out:
			complete_today += 1
			if get_datetime(last_out) > get_datetime(first_in):
				work_hours.append(time_diff_in_hours(last_out, first_in))
		elif first_in and not last_out:
			still_in += 1

	active_employees = frappe.db.count("Employee", {"status": "Active"}) or 0
	mapped_employees = frappe.db.count(
		"Employee", {"status": "Active", "attendance_device_id": ("is", "set")}
	) or 0

	week_labels = []
	week_totals = []
	week_ins = []
	week_outs = []
	for i in range(7):
		day = add_days(week_start, i)
		week_labels.append(formatdate(day, "dd MMM"))
		bucket = daily_counts.get(day) or {"in": 0, "out": 0, "total": 0}
		week_totals.append(bucket["total"])
		week_ins.append(bucket["in"])
		week_outs.append(bucket["out"])

	check_ins_today = (daily_counts.get(today) or {}).get("in", 0)
	check_outs_today = (daily_counts.get(today) or {}).get("out", 0)
	punches_today = (daily_counts.get(today) or {}).get("total", 0)
	punches_week = sum(week_totals)

	presence_rate = round((present_today / active_employees) * 100, 1) if active_employees else 0.0
	complete_rate = round((complete_today / present_today) * 100, 1) if present_today else 0.0
	avg_hours = round(sum(work_hours) / len(work_hours), 2) if work_hours else 0.0

	settings = frappe.db.get_singles_dict("Easy TimePro Settings")
	sync_enabled = int(settings.get("enabled") or 0)

	return {
		"today": formatdate(today, "dd MMM yyyy"),
		"present_today": present_today,
		"active_employees": active_employees,
		"mapped_employees": mapped_employees,
		"presence_rate": presence_rate,
		"complete_today": complete_today,
		"complete_rate": complete_rate,
		"still_in": still_in,
		"avg_hours": avg_hours,
		"check_ins_today": check_ins_today,
		"check_outs_today": check_outs_today,
		"punches_today": punches_today,
		"punches_week": punches_week,
		"sync_enabled": sync_enabled,
		"week_labels": week_labels,
		"week_totals": week_totals,
		"week_ins": week_ins,
		"week_outs": week_outs,
		"max_week": max(week_totals) if week_totals else 0,
	}
