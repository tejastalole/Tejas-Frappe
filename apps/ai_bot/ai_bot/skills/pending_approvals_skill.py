# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

from frappe import _

from ai_bot.services.approvals import format_pending_html, get_pending_documents
from ai_bot.skills.base import BotContext, BotResponse


class PendingApprovalsSkill:
	def match(self, ctx: BotContext) -> bool:
		return bool(
			re.search(
				r"\b(pending approval|pending approvals|awaiting approval|"
				r"pending quotation|pending purchase|pending leave|"
				r"approvals?\s+dikhao|pending approvals?\s+dikhao)\b",
				ctx.message,
				re.I,
			)
		)

	def run(self, ctx: BotContext) -> BotResponse:
		blocks = get_pending_documents()
		actions = []
		for block in blocks:
			for r in block["records"][:3]:
				actions.append(
					{
						"type": "open",
						"doctype": block["doctype"],
						"name": r["name"],
						"label": r["name"],
					}
				)
		return BotResponse(
			reply=format_pending_html(blocks),
			actions=actions[:8],
			context=ctx.filters and {"filters": ctx.filters} or {},
		)
