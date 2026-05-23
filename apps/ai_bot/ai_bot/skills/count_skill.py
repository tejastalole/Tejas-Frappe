# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe

from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.helpers import (
	build_filters,
	create_action,
	format_count_reply,
	list_action,
	resolve_doctype_for_query,
)
from ai_bot.utils.doctypes_map import resolve_doctype


class CountSkill:
	patterns = [
		r"\b(how many|count|number of|total number)\b",
	]

	def match(self, ctx: BotContext) -> bool:
		if re.search(self.patterns[0], ctx.message):
			return True
		return bool(ctx.doctype and re.search(r"^(how many|count)\??$", ctx.message.strip()))

	def run(self, ctx: BotContext) -> BotResponse | None:
		context = {"doctype": ctx.doctype, "filters": ctx.filters} if ctx.doctype else {}
		doctype = resolve_doctype_for_query(ctx.message, context)

		if not doctype:
			phrase_match = re.search(
				r"(?:how many|count|number of)\s+(.+?)(?:\s|$|\?)",
				ctx.message,
				re.I,
			)
			if phrase_match:
				phrase = re.sub(r"\s+(?:whose|where|with|having).*$", "", phrase_match.group(1))
				doctype = resolve_doctype(phrase.strip().lower())

		if not doctype:
			return None

		if not frappe.has_permission(doctype, "read"):
			return BotResponse(
				reply=frappe._("You do not have permission to view {0}.").format(doctype)
			)

		# Use prior filters only when refining the same DocType
		base_filters = {}
		if ctx.doctype == doctype and ctx.filters:
			base_filters = dict(ctx.filters)

		filters = build_filters(ctx.message, doctype, base_filters)
		count = frappe.db.count(doctype, filters)

		return BotResponse(
			reply=format_count_reply(doctype, count, filters),
			actions=[list_action(doctype, filters), create_action(doctype)],
			context={"doctype": doctype, "filters": filters},
		)
