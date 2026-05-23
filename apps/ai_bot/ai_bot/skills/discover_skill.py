# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.utils.doctype_discovery import (
	get_accessible_doctypes,
	get_module_summary,
)


class DiscoverSkill:
	"""List modules, DocTypes, and system overview."""

	patterns = [
		r"\b(what|list|show|tell).*(doctype|document type|module|modules|apps)\b",
		r"\b(what|everything).*(in|inside).*(frappe|erpnext|system|database)\b",
		r"\bwhat can you (do|tell|show)\b",
		r"\blist all (doctype|module)",
		r"\bhow many doctype",
		r"\bwhich module",
	]

	def match(self, ctx: BotContext) -> bool:
		return any(re.search(p, ctx.message) for p in self.patterns)

	def run(self, ctx: BotContext) -> BotResponse | None:
		msg = ctx.message

		# Specific module: "what doctypes in selling"
		module_match = re.search(
			r"(?:in|from|under|module)\s+([a-z][\w\s]*)",
			msg,
			re.I,
		)
		if module_match:
			module = module_match.group(1).strip().title()
			doctypes = get_accessible_doctypes(module=module, limit=50)
			if not doctypes:
				return BotResponse(
					reply=_("No DocTypes found for module <b>{0}</b>.").format(module),
				)
			names = ", ".join(f"<i>{d.name}</i>" for d in doctypes[:25])
			extra = _(" ...and {0} more").format(len(doctypes) - 25) if len(doctypes) > 25 else ""
			return BotResponse(
				reply=_("DocTypes in <b>{0}</b> ({1}):<br>{2}{3}").format(
					module, len(doctypes), names, extra
				),
			)

		# Module summary
		if re.search(r"\b(module|modules)\b", msg):
			summary = get_module_summary()[:12]
			lines = [f"<b>{s['module']}</b>: {s['count']} DocTypes" for s in summary]
			total_dt = sum(s["count"] for s in get_module_summary())
			return BotResponse(
				reply=_(
					"Your site has <b>{0}</b> accessible DocTypes across modules:<br>{1}"
				).format(total_dt, "<br>".join(lines)),
			)

		# General overview
		doctypes = get_accessible_doctypes(limit=500)
		summary = get_module_summary()[:8]
		module_lines = "<br>".join(
			f"• <b>{s['module']}</b> — {s['count']} DocTypes" for s in summary
		)
		sample = ", ".join(d.name for d in doctypes[:15])

		return BotResponse(
			reply=_(
				"I can query your Frappe site. You have access to <b>{0}</b> DocTypes.<br><br>"
				"<b>Top modules:</b><br>{1}<br><br>"
				"<b>Examples:</b> {2} ...<br><br>"
				"Ask <i>how many [DocType]</i>, <i>list customers</i>, "
				"<i>show SAL-ORD-2026-00001</i>, or <i>what doctypes in Stock</i>."
			).format(len(doctypes), module_lines, sample),
		)
