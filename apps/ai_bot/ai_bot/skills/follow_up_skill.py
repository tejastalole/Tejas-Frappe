# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.aggregate_skill import AggregateSkill
from ai_bot.skills.count_skill import CountSkill
from ai_bot.skills.helpers import build_filters, extract_doctype_from_message, is_refinement_query


class FollowUpSkill:
	"""Refine previous query: 'only draft', 'this month', 'grand total is 5000'."""

	def match(self, ctx: BotContext) -> bool:
		if not ctx.doctype:
			return False
		# New DocType in message → let CountSkill handle it
		if extract_doctype_from_message(ctx.message) and not is_refinement_query(ctx.message):
			return False
		return is_refinement_query(ctx.message)

	def run(self, ctx: BotContext) -> BotResponse | None:
		new_filters = build_filters(ctx.message, ctx.doctype, ctx.filters)
		refined = BotContext(
			doctype=ctx.doctype,
			filters=new_filters,
			message=ctx.message,
			raw_message=ctx.raw_message,
		)

		if re.search(r"\b(total|sum|value|amount)\b", ctx.message) and re.search(
			r"\b(total|sum|value of)\b", ctx.message
		):
			return AggregateSkill().run(refined)
		return CountSkill().run(refined)
