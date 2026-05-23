# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

from frappe import _

from ai_bot.services.reports import (
	employee_count_summary,
	format_sales_summary,
	purchase_summary,
	sales_summary,
)
from ai_bot.skills.base import BotContext, BotResponse


class ReportSkill:
	def match(self, ctx: BotContext) -> bool:
		return bool(
			re.search(
				r"\b(sales report|purchase report|employee report|financial summary|"
				r"sales summary|revenue report|आज की सेल्स|sales rport)\b",
				ctx.message,
				re.I,
			)
		)

	def run(self, ctx: BotContext) -> BotResponse:
		if re.search(r"\bemployee", ctx.message, re.I):
			return BotResponse(reply=employee_count_summary(), actions=[])
		if re.search(r"\bpurchase", ctx.message, re.I):
			data = purchase_summary()
			return BotResponse(
				reply=_(
					"<p>Purchase summary since {0}: <b>{1}</b> invoices, total <b>{2}</b>.</p>"
				).format(data["from_date"], data["count"], data["total"]),
				actions=[{"type": "list", "doctype": "Purchase Invoice", "label": _("Purchase Invoices")}],
			)
		data = sales_summary()
		return BotResponse(
			reply=format_sales_summary(data),
			actions=[{"type": "list", "doctype": "Sales Invoice", "label": _("Sales Invoices")}],
		)
