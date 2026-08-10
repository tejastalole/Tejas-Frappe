# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

"""
Cloud REST APIs for the local ZKTeco sync agent.

Authenticate with:
  Authorization: token <api_key>:<api_secret>

Never log API secrets.
"""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime, today

from zkteco_integration.utils.checkin import bulk_create_employee_checkins as _bulk_create
from zkteco_integration.utils.checkin import create_employee_checkin as _create_checkin


def _require_auth():
	"""Ensure caller is an authenticated user (API key session or desk user)."""
	if frappe.session.user in (None, "Guest"):
		frappe.throw(_("Authentication required. Use API Key / API Secret."), frappe.AuthenticationError)


def _parse_records(records) -> list[dict[str, Any]]:
	if records is None:
		return []
	if isinstance(records, str):
		records = json.loads(records)
	if not isinstance(records, list):
		frappe.throw(_("records must be a list"))
	return records


@frappe.whitelist(allow_guest=False)
def create_employee_checkin(
	employee: str | None = None,
	timestamp: str | None = None,
	log_type: str | None = None,
	device_id: str | None = None,
	zkteco_user_id: str | None = None,
) -> dict[str, Any]:
	"""POST /api/method/zkteco_integration.api.create_employee_checkin"""
	_require_auth()
	_assert_device_api_enabled(device_id)
	return _create_checkin(
		employee=employee,
		zkteco_user_id=zkteco_user_id,
		timestamp=timestamp,
		log_type=log_type,
		device_id=device_id,
	)


@frappe.whitelist(allow_guest=False)
def bulk_create_employee_checkins(device_id: str | None = None, records=None) -> dict[str, Any]:
	"""POST /api/method/zkteco_integration.api.bulk_create_employee_checkins"""
	_require_auth()
	device_id = (device_id or "").strip()
	if not device_id:
		frappe.throw(_("device_id is required"))
	_assert_device_api_enabled(device_id)
	parsed = _parse_records(records)
	result = _bulk_create(device_id, parsed)

	# Update device stamps
	if frappe.db.exists("ZKTeco Device", device_id):
		frappe.db.set_value(
			"ZKTeco Device",
			device_id,
			{
				"last_sync": now_datetime(),
				"last_seen": now_datetime(),
				"status": "Online",
				"last_error": None,
			},
			update_modified=False,
		)
		newest = None
		for row in parsed:
			ts = get_datetime(row.get("timestamp") or row.get("time"))
			if ts and (newest is None or ts > newest):
				newest = ts
		if newest:
			current = frappe.db.get_value("ZKTeco Device", device_id, "last_att_stamp")
			if not current or get_datetime(current) < newest:
				frappe.db.set_value("ZKTeco Device", device_id, "last_att_stamp", newest, update_modified=False)

		_write_sync_log(device_id, result)

	frappe.db.commit()
	return result


@frappe.whitelist(allow_guest=False)
def sync_attendance(device_id: str | None = None, records=None) -> dict[str, Any]:
	"""Alias for bulk create — used by local agent."""
	return bulk_create_employee_checkins(device_id=device_id, records=records)


@frappe.whitelist(allow_guest=False)
def device_heartbeat(
	device_id: str | None = None,
	status: str | None = None,
	last_error: str | None = None,
	last_sync: str | None = None,
	last_att_stamp: str | None = None,
) -> dict[str, Any]:
	"""POST /api/method/zkteco_integration.api.device_heartbeat"""
	_require_auth()
	device_id = (device_id or "").strip()
	if not device_id:
		frappe.throw(_("device_id is required"))

	if not frappe.db.exists("ZKTeco Device", device_id):
		# Auto-create placeholder so agent can register
		frappe.get_doc(
			{
				"doctype": "ZKTeco Device",
				"device_name": device_id,
				"ip_address": "0.0.0.0",
				"tcp_port": 4370,
				"enabled": 1,
				"api_enabled": 1,
				"sync_enabled": 1,
				"status": status or "Online",
			}
		).insert(ignore_permissions=True)

	_assert_device_api_enabled(device_id)

	allowed_status = {"Online", "Offline", "Error"}
	st = (status or "Online").strip()
	if st not in allowed_status:
		st = "Online"

	updates = {
		"status": st,
		"last_seen": now_datetime(),
	}
	if last_error is not None:
		updates["last_error"] = (last_error or "")[:1000] or None
	if last_sync:
		updates["last_sync"] = get_datetime(last_sync)
	if last_att_stamp:
		updates["last_att_stamp"] = get_datetime(last_att_stamp)

	frappe.db.set_value("ZKTeco Device", device_id, updates, update_modified=False)
	frappe.db.commit()
	return {"status": "success", "device_id": device_id, "device_status": st}


@frappe.whitelist(allow_guest=False)
def get_device_config(device_id: str | None = None) -> dict[str, Any]:
	"""Return mapping + sync hints for the local agent."""
	_require_auth()
	device_id = (device_id or "").strip()
	if not device_id or not frappe.db.exists("ZKTeco Device", device_id):
		frappe.throw(_("Invalid device_id"))

	device = frappe.get_doc("ZKTeco Device", device_id)
	mappings = frappe.get_all(
		"ZKTeco Employee Mapping",
		filters={"zkteco_device": device_id, "enabled": 1},
		fields=["zkteco_user_id", "employee", "employee_name"],
	)
	return {
		"device_id": device.name,
		"ip_address": device.ip_address,
		"tcp_port": device.tcp_port,
		"sync_interval": device.sync_interval or 60,
		"last_att_stamp": device.last_att_stamp,
		"auto_detect_inout": cint(frappe.db.get_single_value("ZKTeco Settings", "auto_detect_inout")),
		"mappings": mappings,
	}


@frappe.whitelist()
def dashboard_stats() -> dict[str, Any]:
	frappe.only_for(("System Manager", "HR Manager"))
	total = frappe.db.count("ZKTeco Device")
	online = frappe.db.count("ZKTeco Device", {"status": "Online"})
	offline = frappe.db.count("ZKTeco Device", {"status": "Offline"})
	error = frappe.db.count("ZKTeco Device", {"status": "Error"})
	day = today()
	checkins = frappe.db.count(
		"Employee Checkin",
		{"time": ("between", [f"{day} 00:00:00", f"{day} 23:59:59"]), "log_type": "IN"},
	)
	checkouts = frappe.db.count(
		"Employee Checkin",
		{"time": ("between", [f"{day} 00:00:00", f"{day} 23:59:59"]), "log_type": "OUT"},
	)
	failed = frappe.db.count("ZKTeco Sync Log", {"status": "Failed", "creation": (">=", f"{day} 00:00:00")})
	last_sync = frappe.db.get_value("ZKTeco Device", {}, "last_sync", order_by="last_sync desc")
	return {
		"total_devices": total,
		"online_devices": online,
		"offline_devices": offline,
		"error_devices": error,
		"todays_checkins": checkins,
		"todays_checkouts": checkouts,
		"failed_syncs": failed,
		"last_sync": last_sync,
	}


def _assert_device_api_enabled(device_id: str | None):
	if not device_id:
		return
	if not frappe.db.exists("ZKTeco Device", device_id):
		return
	row = frappe.db.get_value("ZKTeco Device", device_id, ["enabled", "api_enabled"], as_dict=True)
	if row and (not row.enabled or not row.api_enabled):
		frappe.throw(_("API disabled for device {0}").format(device_id))


def _write_sync_log(device_id: str, result: dict[str, Any]):
	status = "Success"
	if result.get("failed") and result.get("created"):
		status = "Partial Success"
	elif result.get("failed") and not result.get("created"):
		status = "Failed"
	frappe.get_doc(
		{
			"doctype": "ZKTeco Sync Log",
			"device": device_id,
			"sync_started": now_datetime(),
			"sync_completed": now_datetime(),
			"status": status,
			"total_records": result.get("total") or 0,
			"new_records": result.get("created") or 0,
			"duplicate_records": result.get("duplicate") or 0,
			"failed_records": result.get("failed") or 0,
			"error_message": "\n".join(result.get("errors") or [])[:2000] or None,
		}
	).insert(ignore_permissions=True)
