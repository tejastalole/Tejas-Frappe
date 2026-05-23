# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.helpers import extract_doctype_from_message, form_action
from ai_bot.utils.doctypes_map import list_supported_doctypes


class OpenRecordSkill:
	pattern = r"\b(show|open|view|display|go to)\b"

	def match(self, ctx: BotContext) -> bool:
		if re.search(self.pattern, ctx.message) and re.search(
			r"[A-Z]{2,}[-\w\d]+", ctx.raw_message
		):
			return True
		return False

	def run(self, ctx: BotContext) -> BotResponse | None:
		name_match = re.search(r"\b([A-Z]{2,}[-][\w\d-]+)\b", ctx.raw_message)
		if not name_match:
			return None

		name = name_match.group(1)
		doctype = ctx.doctype or extract_doctype_from_message(ctx.message)

		if not doctype:
			for dt in list_supported_doctypes():
				if frappe.db.exists(dt, name):
					doctype = dt
					break

		if not doctype or not frappe.db.exists(doctype, name):
			return BotResponse(
				reply=_("Could not find document <b>{0}</b>.").format(name),
			)

		if not frappe.has_permission(doctype, "read", name):
			return BotResponse(
				reply=_("You do not have permission to view {0}.").format(name),
			)

		return BotResponse(
			reply=_("Found <b>{0}</b>. Click below to open it.").format(name),
			actions=[form_action(doctype, name)],
			context={"doctype": doctype, "filters": {}},
		)
