# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.copilot.security import has_create, has_read, log_action
from ai_bot.skills.base import BotContext, BotResponse


class CrmSkill:
	def match(self, ctx: BotContext) -> bool:
		return bool(
			re.search(
				r"\b(lead|opportunity|crm|follow.?up|customer history)\b",
				ctx.message,
				re.I,
			)
			and re.search(r"\b(create|new|show|list|next|history)\b", ctx.message, re.I)
		)

	def run(self, ctx: BotContext) -> BotResponse:
		if re.search(r"\bcreate\b.*\blead\b|\blead\b.*\bcreate\b|\bnew lead\b", ctx.message, re.I):
			return self._create_lead(ctx)
		if re.search(r"\bopportunit", ctx.message, re.I):
			return self._list_opportunities(ctx)
		if re.search(r"\bfollow", ctx.message, re.I):
			return self._follow_ups(ctx)
		return BotResponse(
			reply=_("Try: <i>Create lead Rahul from Pune</i> or <i>Show today's opportunities</i>."),
			actions=[],
		)

	def _create_lead(self, ctx: BotContext) -> BotResponse:
		if not frappe.db.exists("DocType", "Lead"):
			return BotResponse(reply=_("Lead DocType is not available."), actions=[])
		if not has_create("Lead"):
			return BotResponse(reply=_("You cannot create Leads."), actions=[])

		name_m = re.search(
			r"(?:lead|for)\s+([A-Za-z][A-Za-z\s]{1,40}?)(?:\s+from|\s+in|$)",
			ctx.raw_message,
			re.I,
		)
		city_m = re.search(r"\bfrom\s+([A-Za-z\s]{2,30})", ctx.raw_message, re.I)
		lead_name = (name_m.group(1).strip() if name_m else "New Lead")[:140]
		doc = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": lead_name,
				"status": "Lead",
			}
		)
		if city_m:
			doc.city = city_m.group(1).strip()
		doc.insert(ignore_permissions=False)
		log_action("create", "Lead", doc.name)
		return BotResponse(
			reply=_("Lead <b>{0}</b> created successfully.").format(doc.name),
			actions=[
				{"type": "open", "doctype": "Lead", "name": doc.name, "label": doc.name},
			],
			context={"doctype": "Lead"},
		)

	def _list_opportunities(self, ctx: BotContext) -> BotResponse:
		if not frappe.db.exists("DocType", "Opportunity"):
			return BotResponse(reply=_("Opportunity DocType is not available."), actions=[])
		if not has_read("Opportunity"):
			return BotResponse(reply=_("No access to Opportunities."), actions=[])

		records = frappe.get_all(
			"Opportunity",
			fields=["name", "party_name", "opportunity_amount", "status"],
			order_by="creation desc",
			limit=8,
		)
		if not records:
			return BotResponse(reply=_("No opportunities found."), actions=[])
		lines = "".join(
			f"<li><b>{r.name}</b> — {r.party_name or ''} ({r.status or ''})</li>"
			for r in records
		)
		return BotResponse(
			reply=_("<p>Recent opportunities:</p><ul>{0}</ul>").format(lines),
			actions=[
				{"type": "open", "doctype": "Opportunity", "name": r.name, "label": r.name}
				for r in records[:5]
			],
		)

	def _follow_ups(self, ctx: BotContext) -> BotResponse:
		if not frappe.db.exists("DocType", "ToDo"):
			return BotResponse(reply=_("No follow-up tasks found."), actions=[])
		todos = frappe.get_all(
			"ToDo",
			filters={"status": "Open", "reference_type": ["in", ["Lead", "Opportunity", "Customer"]]},
			fields=["name", "description", "reference_type", "reference_name", "date"],
			order_by="date asc",
			limit=8,
		)
		if not todos:
			return BotResponse(reply=_("No open follow-ups."), actions=[])
		lines = "".join(
			f"<li>{t.description or t.name} — {t.reference_type} {t.reference_name}</li>"
			for t in todos
		)
		return BotResponse(reply=_("<p>Next follow-ups:</p><ul>{0}</ul>").format(lines), actions=[])
