# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

from frappe import _

from ai_bot.copilot.security import log_action
from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.helpers import resolve_doctype_from_message


class WorkflowSkill:
	"""Approve / reject / submit phrasing with doc name."""

	def match(self, ctx: BotContext) -> bool:
		if not re.search(r"\b(approve|reject|submit)\b", ctx.message, re.I):
			return False
		return bool(re.search(r"\b[A-Z]{2,}[-][A-Z0-9-]+\b", ctx.raw_message))

	def run(self, ctx: BotContext) -> BotResponse:
		from ai_bot.copilot.executor import execute_intent

		action = "approve"
		if re.search(r"\breject\b", ctx.message, re.I):
			action = "reject"
		elif re.search(r"\bsubmit\b", ctx.message, re.I):
			action = "approve"

		name_m = re.search(r"\b([A-Z]{2,}[-][A-Z0-9-]+)\b", ctx.raw_message)
		name = name_m.group(1) if name_m else None
		doctype = resolve_doctype_from_message(ctx.raw_message) or ctx.doctype

		if not doctype or not name:
			return BotResponse(
				reply=_("Please specify document type and ID (e.g. Approve PO-00012)."),
				actions=[],
			)

		intent = {
			"action": action,
			"doctype": doctype,
			"filters": {"name": name},
			"status": "success",
		}
		result = execute_intent(intent, ctx.raw_message)
		log_action(action, doctype, name)
		return BotResponse(
			reply=result.get("message", ""),
			actions=result.get("actions") or [],
			context={"doctype": doctype, "last_intent": intent},
			intent=intent,
		)
