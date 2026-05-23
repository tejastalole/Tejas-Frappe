# Copyright (c) 2026, Tejas and contributors
# MIT License

from frappe import _

from ai_bot.copilot.persona import CAPABILITIES, get_welcome_message
from ai_bot.skills.base import BotContext, BotResponse


class HelpSkill:
	def match(self, ctx: BotContext) -> bool:
		return True

	def run(self, ctx: BotContext) -> BotResponse:
		caps = "".join(f"<li>{c}</li>" for c in CAPABILITIES)
		return BotResponse(
			reply=get_welcome_message()
			+ _("<p><b>I can help with:</b></p><ul>{0}</ul>").format(caps),
			actions=[],
			context=ctx.filters and {"doctype": ctx.doctype, "filters": ctx.filters} or {},
		)
