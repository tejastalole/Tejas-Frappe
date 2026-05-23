# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.skills.base import BotContext, BotResponse
from ai_bot.skills.helpers import form_action
from ai_bot.utils.create_sales_order import create_sales_order, parse_create_so_params


class CreateSalesOrderSkill:
	pattern = r"\b(create|make|new)\b.*\b(sales order|sales orders|so)\b"

	def match(self, ctx: BotContext) -> bool:
		return bool(re.search(self.pattern, ctx.message))

	def run(self, ctx: BotContext) -> BotResponse | None:
		params = parse_create_so_params(ctx.raw_message)
		if not params:
			return BotResponse(
				reply=_(
					"To create a Sales Order, try:<br>"
					"<i>Create sales order for customer Tejas item Bat qty 110</i><br>"
					"<i>Create a Sales Order and add item Bat with qty 110</i>"
				),
			)

		if params.get("needs_customer"):
			return BotResponse(
				reply=_(
					"I found item <b>{0}</b> (qty <b>{1}</b>). "
					"Please add a customer, e.g.: "
					"<i>Create sales order for customer Tejas item {0} qty {1}</i>"
				).format(params["item_code"], params["qty"]),
			)

		try:
			so = create_sales_order(
				customer=params["customer"],
				item_code=params["item_code"],
				qty=params["qty"],
				rate=params.get("rate"),
			)
		except frappe.ValidationError as e:
			return BotResponse(reply=str(e))
		except frappe.PermissionError as e:
			return BotResponse(reply=str(e))
		except Exception as e:
			frappe.log_error(message=frappe.get_traceback(), title="AI Bot Create Sales Order")
			return BotResponse(
				reply=_("Could not create Sales Order: {0}").format(str(e)),
			)

		item_line = so.items[0] if so.items else None
		rate_text = frappe.format_value(item_line.rate, {"fieldtype": "Currency"}) if item_line else ""
		qty_text = item_line.qty if item_line else params["qty"]

		return BotResponse(
			reply=_(
				"Created Sales Order <b>{0}</b> for customer <b>{1}</b><br>"
				"Item: <b>{2}</b> · Qty: <b>{3}</b> · Rate: <b>{4}</b>"
			).format(so.name, so.customer_name or so.customer, params["item_code"], qty_text, rate_text),
			actions=[form_action("Sales Order", so.name)],
			context={"doctype": "Sales Order", "filters": {}},
		)
