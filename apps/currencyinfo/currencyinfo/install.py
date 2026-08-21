# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


DEFAULT_STREAM = "wss://stream.binance.com:9443/ws/btcusdt@trade"


def after_install():
	ensure_settings()
	ensure_workspace()
	_start_stream()


def after_migrate():
	ensure_settings()
	ensure_workspace()
	_start_stream()


def ensure_settings():
	if not frappe.db.exists("DocType", "Currency Info Settings"):
		return
	doc = frappe.get_single("Currency Info Settings")
	changed = False
	if not doc.stream_url:
		doc.stream_url = DEFAULT_STREAM
		changed = True
	if not doc.symbol:
		doc.symbol = "BTCUSDT"
		changed = True
	if doc.enabled is None:
		doc.enabled = 1
		changed = True
	if changed:
		doc.save(ignore_permissions=True)


def ensure_workspace():
	"""Ensure workspace exists after fixtures / JSON import via migrate."""
	if frappe.db.exists("Workspace", "Currency Info"):
		return
	# Workspace JSON is imported via modules; create a minimal one if missing
	try:
		ws = frappe.get_doc(
			{
				"doctype": "Workspace",
				"name": "Currency Info",
				"label": "Currency Info",
				"title": "Currency Info",
				"module": "Currency Info",
				"public": 1,
				"icon": "stock",
				"indicator_color": "blue",
				"content": frappe.as_json(
					[
						{
							"id": "hdr",
							"type": "header",
							"data": {
								"text": '<span class="h4"><b>Currency Info</b></span>',
								"col": 12,
							},
						},
						{
							"id": "sc_live",
							"type": "shortcut",
							"data": {"shortcut_name": "Live Feed", "col": 4},
						},
						{
							"id": "sc_settings",
							"type": "shortcut",
							"data": {"shortcut_name": "Settings", "col": 4},
						},
					]
				),
				"shortcuts": [
					{
						"label": "Live Feed",
						"type": "Page",
						"link_to": "currency-info-live",
						"color": "Blue",
						"icon": "trending-up",
					},
					{
						"label": "Settings",
						"type": "DocType",
						"link_to": "Currency Info Settings",
						"color": "Gray",
						"icon": "setting-gear",
					},
				],
			}
		)
		ws.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Currency Info workspace setup", message=frappe.get_traceback())


def _start_stream():
	try:
		from currencyinfo.currency_info.stream import ensure_stream_loop

		ensure_stream_loop(force=True)
	except Exception:
		frappe.log_error(title="Currency Info stream start failed", message=frappe.get_traceback())
