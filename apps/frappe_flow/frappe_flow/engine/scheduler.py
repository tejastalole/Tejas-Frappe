# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import now_datetime, get_time, getdate, today

from frappe_flow.engine.executor import execute_flow


def run_hourly_flows():
	_run_scheduled("Hourly")


def run_daily_flows():
	_run_scheduled("Daily")


def run_weekly_flows():
	_run_scheduled("Weekly")


def run_monthly_flows():
	_run_scheduled("Monthly")


def _run_scheduled(frequency):
	schedules = frappe.get_all(
		"FF Flow Schedule",
		filters={"is_active": 1, "frequency": frequency},
		fields=["name", "flow", "run_time", "day_of_week"],
	)
	now = now_datetime()
	for sched in schedules:
		flow = frappe.db.get_value(
			"FF Flow Automation",
			sched.flow,
			["name", "is_active", "status", "trigger_type"],
			as_dict=True,
		)
		if not flow or not flow.is_active or flow.status != "Active":
			continue
		if not _should_run_now(sched, frequency, now):
			continue
		try:
			execute_flow(flow.name)
		except Exception:
			frappe.log_error(title=f"Scheduled flow failed: {flow.name}")


def _should_run_now(schedule, frequency, now):
	if frequency == "Hourly":
		return True
	if frequency == "Daily" and schedule.run_time:
		return get_time(schedule.run_time).hour == now.hour
	if frequency == "Weekly" and schedule.day_of_week:
		return now.strftime("%A") == schedule.day_of_week
	if frequency == "Monthly":
		return now.day == 1
	return True
