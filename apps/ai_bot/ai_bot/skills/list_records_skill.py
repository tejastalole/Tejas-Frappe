# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.helpers import create_action, list_action, resolve_doctype_for_query
from ai_bot.utils.doctype_discovery import discover_doctype, get_recent_records


class ListRecordsSkill:
	pattern = r"\b(list|show|display|get|fetch)\b"

	def match(self, ctx: BotContext) -> bool:
		if not re.search(self.pattern, ctx.message):
			return False
		# Avoid conflicting with open record by name
		if re.search(r"[A-Z]{2,}[-][\w\d-]+", ctx.raw_message):
			return False
		if re.search(r"\b(doctype|module|everything)\b", ctx.message):
			return False
		return bool(discover_doctype(ctx.message) or resolve_doctype_for_query(ctx.message, {}))

	def run(self, ctx: BotContext) -> BotResponse | None:
		phrase = re.sub(
			r"^(?:list|show|display|get|fetch)\s+(?:all\s+|me\s+|the\s+)?",
			"",
			ctx.message,
			flags=re.I,
		).strip()
		context = {"doctype": ctx.doctype} if ctx.doctype else {}
		doctype = (
			resolve_doctype_for_query(ctx.message, context)
			or discover_doctype(phrase)
			or discover_doctype(ctx.message)
		)

		if not doctype:
			return None

		if not frappe.has_permission(doctype, "read"):
			return BotResponse(
				reply=_("You do not have permission to view {0}.").format(doctype),
			)

		records = get_recent_records(doctype, limit=8)
		total = frappe.db.count(doctype)
		label = frappe.unscrub(doctype)

		if not records:
			return BotResponse(
				reply=_("No <b>{0}</b> records found.").format(label),
				actions=[create_action(doctype)],
				context={"doctype": doctype, "filters": {}},
			)

		lines = []
		for r in records:
			title = r.get("title") or r.get("name")
			lines.append(f"• <b>{r.name}</b>" + (f" — {title}" if title != r.name else ""))

		return BotResponse(
			reply=_(
				"Latest <b>{0}</b> ({1} total):<br>{2}"
			).format(label, total, "<br>".join(lines)),
			actions=[list_action(doctype, {}), create_action(doctype)],
			context={"doctype": doctype, "filters": {}},
		)
