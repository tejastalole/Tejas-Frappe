# Copyright (c) 2026, Tejas and contributors
# MIT License

from frappe import _

from ai_bot.services.developer import (
	generate_client_script,
	generate_server_script,
	generate_sql_hint,
	match_developer_request,
)
from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.helpers import resolve_doctype_from_message


class DeveloperSkill:
	def match(self, ctx: BotContext) -> bool:
		return match_developer_request(ctx.message)

	def run(self, ctx: BotContext) -> BotResponse:
		doctype = resolve_doctype_from_message(ctx.raw_message)
		lower = ctx.message

		if "server script" in lower:
			code = generate_server_script(ctx.raw_message, doctype)
			label = _("Server Script")
		elif "sql" in lower:
			code = generate_sql_hint(ctx.raw_message)
			label = _("SQL")
		else:
			code = generate_client_script(ctx.raw_message, doctype)
			label = _("Client Script")

		return BotResponse(
			reply=_("<p><b>{0}</b> (copy to Customize):</p><pre><code>{1}</code></pre>").format(
				label, frappe.utils.escape_html(code)
			),
			actions=[],
		)
