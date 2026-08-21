# Copyright (c) 2026, Tejas and contributors
# MIT License

import json
import os

import frappe
from frappe.modules.import_file import import_file_by_path


def after_install():
	ensure_settings()
	sync_dashboard_artifacts()
	ensure_workspace()
	_start_sync_loop()


def after_migrate():
	ensure_settings()
	sync_dashboard_artifacts()
	ensure_workspace()
	_start_sync_loop()


def _start_sync_loop():
	try:
		from easytimepro.easy_timepro.sync import ensure_realtime_loop

		ensure_realtime_loop(force=True)
	except Exception:
		frappe.log_error(title="Easy TimePro loop start failed", message=frappe.get_traceback())


def ensure_settings():
	settings = frappe.get_single("Easy TimePro Settings")
	changed = False
	if not settings.base_url:
		settings.base_url = "http://192.168.10.30:8082"
		changed = True
	if not settings.username:
		settings.username = "admin"
		changed = True
	if not settings.get_password("password", raise_exception=False):
		settings.password = "Admin@123"
		changed = True
	if settings.enabled is None:
		settings.enabled = 1
		changed = True
	# New field: seconds (default 5). Drop legacy minutes if present in memory.
	if not settings.get("sync_interval_seconds"):
		settings.sync_interval_seconds = 5
		changed = True
	if settings.create_employee_checkin is None:
		settings.create_employee_checkin = 1
		changed = True
	if changed:
		settings.save(ignore_permissions=True)


def _app_path(*parts: str) -> str:
	return os.path.join(frappe.get_app_path("easytimepro"), *parts)


def sync_dashboard_artifacts():
	"""Import number cards and charts from app JSON files."""
	roots = [
		_app_path("easy_timepro", "number_card"),
		_app_path("easy_timepro", "dashboard_chart"),
		_app_path("easy_timepro", "custom_html_block"),
	]
	for root in roots:
		if not os.path.isdir(root):
			continue
		for dirpath, _dirnames, filenames in os.walk(root):
			for filename in filenames:
				if not filename.endswith(".json"):
					continue
				path = os.path.join(dirpath, filename)
				try:
					import_file_by_path(path, force=True)
				except Exception:
					frappe.log_error(
						title=f"Easy TimePro import failed: {filename}",
						message=frappe.get_traceback(),
					)


def ensure_workspace():
	workspace_path = _app_path("easy_timepro", "workspace", "easy_timepro", "easy_timepro.json")
	if not os.path.exists(workspace_path):
		return

	with open(workspace_path, encoding="utf-8") as handle:
		data = json.load(handle)

	# Keep only Workspace-safe keys
	allowed = {
		"label",
		"title",
		"module",
		"public",
		"is_hidden",
		"icon",
		"indicator_color",
		"content",
		"links",
		"shortcuts",
		"charts",
		"number_cards",
		"custom_blocks",
		"hide_custom",
		"for_user",
	}
	payload = {key: data[key] for key in allowed if key in data}
	payload["name"] = "Easy TimePro"
	payload["label"] = "Easy TimePro"
	payload["title"] = "Easy TimePro"
	payload["module"] = "Easy TimePro"
	payload["public"] = 1
	payload["is_hidden"] = 0

	if frappe.db.exists("Workspace", "Easy TimePro"):
		ws = frappe.get_doc("Workspace", "Easy TimePro")
		ws.update(payload)
		ws.set("links", [])
		for row in payload.get("links") or []:
			ws.append("links", row)
		ws.set("shortcuts", [])
		for row in payload.get("shortcuts") or []:
			ws.append("shortcuts", row)
		ws.set("charts", [])
		for row in payload.get("charts") or []:
			ws.append("charts", row)
		ws.set("number_cards", [])
		for row in payload.get("number_cards") or []:
			ws.append("number_cards", row)
		ws.set("custom_blocks", [])
		for row in payload.get("custom_blocks") or []:
			ws.append("custom_blocks", row)
		ws.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "Workspace", **payload})
		doc.insert(ignore_permissions=True)
