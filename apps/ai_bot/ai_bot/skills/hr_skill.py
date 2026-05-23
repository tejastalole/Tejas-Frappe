# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.copilot.security import has_read
from ai_bot.skills.base import BotContext, BotResponse


class HrSkill:
	def match(self, ctx: BotContext) -> bool:
		return bool(
			re.search(
				r"\b(leave|attendance|salary slip|remaining leave|apply leave|"
				r"chutti|attendance|salary)\b",
				ctx.message,
				re.I,
			)
		)

	def run(self, ctx: BotContext) -> BotResponse:
		if re.search(r"\bleave balance|remaining leave", ctx.message, re.I):
			return self._leave_balance()
		if re.search(r"\bsalary slip", ctx.message, re.I):
			return self._salary_slips()
		if re.search(r"\battendance", ctx.message, re.I):
			return self._attendance()
		if re.search(r"\bapply leave", ctx.message, re.I):
			return BotResponse(
				reply=_(
					"Open <b>Leave Application</b> from HR module to apply leave, "
					"or say: <i>create leave application</i>."
				),
				actions=[{"type": "create", "doctype": "Leave Application", "label": _("New Leave")}],
			)
		return self._pending_leave()

	def _leave_balance(self) -> BotResponse:
		user = frappe.session.user
		if not frappe.db.exists("DocType", "Leave Allocation"):
			return BotResponse(reply=_("Leave module not available."), actions=[])
		employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not employee:
			return BotResponse(reply=_("No employee linked to your user."), actions=[])
		allocations = frappe.get_all(
			"Leave Allocation",
			filters={"employee": employee, "docstatus": 1},
			fields=["leave_type", "total_leaves_allocated", "total_leaves_encashed"],
			limit=10,
		)
		if not allocations:
			return BotResponse(reply=_("No leave allocation found."), actions=[])
		lines = "".join(
			f"<li>{a.leave_type}: {a.total_leaves_allocated} allocated</li>" for a in allocations
		)
		return BotResponse(reply=_("<p>Leave balance:</p><ul>{0}</ul>").format(lines), actions=[])

	def _salary_slips(self) -> BotResponse:
		if not has_read("Salary Slip"):
			return BotResponse(reply=_("No access to salary slips."), actions=[])
		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		filters = {"docstatus": 1}
		if employee:
			filters["employee"] = employee
		slips = frappe.get_all(
			"Salary Slip",
			filters=filters,
			fields=["name", "start_date", "end_date", "net_pay"],
			order_by="end_date desc",
			limit=6,
		)
		if not slips:
			return BotResponse(reply=_("No salary slips found."), actions=[])
		lines = "".join(
			f"<li><b>{s.name}</b> — {s.start_date} to {s.end_date}</li>" for s in slips
		)
		return BotResponse(
			reply=_("<p>Salary slips:</p><ul>{0}</ul>").format(lines),
			actions=[
				{"type": "open", "doctype": "Salary Slip", "name": s.name, "label": s.name}
				for s in slips[:4]
			],
		)

	def _attendance(self) -> BotResponse:
		if not has_read("Attendance"):
			return BotResponse(reply=_("No access to attendance."), actions=[])
		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if not employee:
			return BotResponse(reply=_("No employee linked to your user."), actions=[])
		count = frappe.db.count(
			"Attendance",
			{"employee": employee, "attendance_date": [">=", frappe.utils.add_days(frappe.utils.today(), -30)]},
		)
		return BotResponse(
			reply=_("Attendance records in last 30 days: <b>{0}</b>.").format(count),
			actions=[{"type": "list", "doctype": "Attendance", "label": _("Attendance")}],
		)

	def _pending_leave(self) -> BotResponse:
		if not has_read("Leave Application"):
			return BotResponse(reply=_("Leave Application not available."), actions=[])
		records = frappe.get_all(
			"Leave Application",
			filters={"docstatus": 0},
			fields=["name", "employee_name", "leave_type", "from_date"],
			limit=8,
		)
		if not records:
			return BotResponse(reply=_("No pending leave applications."), actions=[])
		lines = "".join(
			f"<li><b>{r.name}</b> — {r.employee_name} ({r.leave_type})</li>" for r in records
		)
		return BotResponse(
			reply=_("<p>Pending leave applications:</p><ul>{0}</ul>").format(lines),
			actions=[
				{"type": "open", "doctype": "Leave Application", "name": r.name, "label": r.name}
				for r in records[:5]
			],
		)
