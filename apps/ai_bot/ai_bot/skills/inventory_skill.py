# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

import frappe
from frappe import _

from ai_bot.copilot.security import has_read
from ai_bot.skills.base import BotContext, BotResponse


class InventorySkill:
	def match(self, ctx: BotContext) -> bool:
		return bool(
			re.search(
				r"\b(stock|warehouse|inventory|low stock|reorder|material request|"
				r"item availability|available qty)\b",
				ctx.message,
				re.I,
			)
		)

	def run(self, ctx: BotContext) -> BotResponse:
		if re.search(r"\blow stock|reorder", ctx.message, re.I):
			return self._low_stock()
		if re.search(r"\bmaterial request", ctx.message, re.I):
			return self._material_requests()
		if re.search(r"\bwarehouse", ctx.message, re.I):
			return self._warehouse_hint(ctx)
		return self._item_stock(ctx)

	def _low_stock(self) -> BotResponse:
		if not has_read("Item"):
			return BotResponse(reply=_("No access to items."), actions=[])
		if not frappe.db.exists("DocType", "Bin"):
			return BotResponse(reply=_("Stock/Bin not available."), actions=[])

		items = frappe.db.sql(
			"""
			SELECT i.name, i.item_name, SUM(b.actual_qty) AS qty, i.reorder_level
			FROM `tabItem` i
			LEFT JOIN `tabBin` b ON b.item_code = i.name
			WHERE i.is_stock_item = 1 AND i.disabled = 0
			GROUP BY i.name
			HAVING qty <= IFNULL(i.reorder_level, 0) AND IFNULL(i.reorder_level, 0) > 0
			LIMIT 15
			""",
			as_dict=True,
		)
		if not items:
			return BotResponse(reply=_("No low-stock items (reorder level) found."), actions=[])
		lines = "".join(
			f"<li><b>{i.name}</b> — qty {i.qty} (reorder {i.reorder_level})</li>" for i in items
		)
		return BotResponse(
			reply=_("<p>Low stock / reorder alerts:</p><ul>{0}</ul>").format(lines),
			actions=[{"type": "open", "doctype": "Item", "name": i.name, "label": i.name} for i in items[:5]],
		)

	def _material_requests(self) -> BotResponse:
		if not has_read("Material Request"):
			return BotResponse(reply=_("No access to Material Request."), actions=[])
		records = frappe.get_all(
			"Material Request",
			filters={"docstatus": ["<", 2]},
			fields=["name", "material_request_type", "status"],
			order_by="modified desc",
			limit=8,
		)
		if not records:
			return BotResponse(reply=_("No material requests found."), actions=[])
		lines = "".join(f"<li><b>{r.name}</b> — {r.status}</li>" for r in records)
		return BotResponse(
			reply=_("<p>Material requests:</p><ul>{0}</ul>").format(lines),
			actions=[
				{"type": "open", "doctype": "Material Request", "name": r.name, "label": r.name}
				for r in records[:5]
			],
		)

	def _warehouse_hint(self, ctx: BotContext) -> BotResponse:
		if not has_read("Warehouse"):
			return BotResponse(reply=_("No access to warehouses."), actions=[])
		wh = frappe.get_all("Warehouse", fields=["name"], limit=10)
		lines = "".join(f"<li>{w.name}</li>" for w in wh)
		return BotResponse(
			reply=_("<p>Warehouses:</p><ul>{0}</ul>").format(lines),
			actions=[{"type": "list", "doctype": "Warehouse", "label": _("Warehouses")}],
		)

	def _item_stock(self, ctx: BotContext) -> BotResponse:
		item_m = re.search(r"\bitem\s+([A-Za-z0-9\-]+)", ctx.raw_message, re.I)
		if item_m and has_read("Bin"):
			code = item_m.group(1)
			qty = frappe.db.sql(
				"SELECT SUM(actual_qty) FROM `tabBin` WHERE item_code = %s",
				code,
			)[0][0]
			return BotResponse(
				reply=_("Item <b>{0}</b> total stock: <b>{1}</b>.").format(code, qty or 0),
				actions=[{"type": "open", "doctype": "Item", "name": code, "label": code}],
			)
		return BotResponse(
			reply=_("Try: <i>low stock items</i> or <i>warehouse stock</i>."),
			actions=[{"type": "list", "doctype": "Item", "label": _("Items")}],
		)
