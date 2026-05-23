# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe

from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.helpers import (
	build_filters,
	create_action,
	format_sum_reply,
	list_action,
	resolve_doctype_for_query,
)
from ai_bot.utils.doctypes_map import get_config


class AggregateSkill:
	pattern = r"\b(total|sum|value|amount|revenue)\b"

	def match(self, ctx: BotContext) -> bool:
		# "how many sales orders with grand total 5000" → count, not sum
		if re.search(r"\b(how many|count|number of)\b", ctx.message):
			return False
		if re.search(r"\bgrand total\s*(?:is|=|>|<|greater|less|above|below)\b", ctx.message):
			return False
		return bool(
			re.search(r"\b(total value|sum of|sum|total amount|revenue)\b", ctx.message)
			or re.search(r"\b(total|value|amount)\s+of\b", ctx.message)
		)

	def run(self, ctx: BotContext) -> BotResponse | None:
		context = {"doctype": ctx.doctype, "filters": ctx.filters} if ctx.doctype else {}
		doctype = resolve_doctype_for_query(ctx.message, context)
		if not doctype:
			return None

		config = get_config(doctype)
		amount_field = config.get("amount_field")
		if not amount_field:
			return None

		if not frappe.has_permission(doctype, "read"):
			return BotResponse(
				reply=frappe._("You do not have permission to view {0}.").format(doctype)
			)

		base_filters = dict(ctx.filters) if ctx.doctype == doctype and ctx.filters else {}
		filters = build_filters(ctx.message, doctype, base_filters)
		total = _sum_field(doctype, amount_field, filters)

		return BotResponse(
			reply=format_sum_reply(doctype, total, filters),
			actions=[list_action(doctype, filters), create_action(doctype)],
			context={"doctype": doctype, "filters": filters},
		)


def _sum_field(doctype: str, field: str, filters: dict) -> float:
	conditions = []
	values = []
	for key, val in filters.items():
		if isinstance(val, list) and len(val) == 2 and val[0] == "between":
			conditions.append(f"`{key}` between %s and %s")
			values.extend(val[1])
		elif isinstance(val, (list, tuple)) and len(val) == 2:
			conditions.append(f"`{key}` {val[0]} %s")
			values.append(val[1])
		else:
			conditions.append(f"`{key}` = %s")
			values.append(val)

	where = " AND ".join(conditions) if conditions else "1=1"
	result = frappe.db.sql(
		f"SELECT COALESCE(SUM(`{field}`), 0) FROM `tab{doctype}` WHERE {where}",
		tuple(values),
	)
	return float(result[0][0] if result else 0)
