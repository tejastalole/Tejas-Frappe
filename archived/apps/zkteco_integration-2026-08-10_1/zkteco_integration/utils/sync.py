# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

"""On-site device sync (LAN). Production cloud uses local agent + API instead."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import get_datetime, now_datetime

from zkteco_integration.utils.checkin import create_employee_checkin
from zkteco_integration.utils.device_client import fetch_attendance


def sync_device(device_name: str, full_sync: bool = False) -> dict[str, Any]:
	device = frappe.get_doc("ZKTeco Device", device_name)
	if not device.enabled or not device.sync_enabled:
		return {"status": "Failed", "device": device_name, "error": "Device sync disabled"}

	started = now_datetime()
	log = frappe.get_doc(
		{
			"doctype": "ZKTeco Sync Log",
			"device": device_name,
			"sync_started": started,
			"status": "Failed",
			"total_records": 0,
			"new_records": 0,
			"duplicate_records": 0,
			"failed_records": 0,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	try:
		since = None if full_sync else get_datetime(device.last_att_stamp) if device.last_att_stamp else None
		rows = fetch_attendance(device_name, since=since)
		# Sort ascending for IN/OUT sequence
		rows.sort(key=lambda r: get_datetime(r["timestamp"]))

		new = dup = failed = 0
		max_stamp = since
		for row in rows:
			result = create_employee_checkin(
				zkteco_user_id=row["zkteco_user_id"],
				timestamp=row["timestamp"],
				device_id=device_name,
				punch_status=row.get("punch_status"),
				punch=row.get("punch"),
			)
			st = result.get("status")
			if st == "success":
				new += 1
			elif st == "duplicate":
				dup += 1
			else:
				failed += 1

			ts = get_datetime(row["timestamp"])
			if max_stamp is None or (ts and ts > max_stamp):
				max_stamp = ts

		status = "Success"
		if failed and new:
			status = "Partial Success"
		elif failed and not new:
			status = "Failed"

		log.status = status
		log.total_records = len(rows)
		log.new_records = new
		log.duplicate_records = dup
		log.failed_records = failed
		log.sync_completed = now_datetime()
		log.save(ignore_permissions=True)

		updates = {"last_sync": now_datetime(), "status": "Online", "last_error": None}
		if max_stamp:
			updates["last_att_stamp"] = max_stamp
		device.db_set(updates, update_modified=False)
		frappe.db.commit()

		return {
			"status": status,
			"device": device_name,
			"total_records": len(rows),
			"new_records": new,
			"duplicate_records": dup,
			"failed_records": failed,
			"sync_log": log.name,
		}
	except Exception as exc:
		log.status = "Failed"
		log.error_message = frappe.get_traceback()
		log.sync_completed = now_datetime()
		log.save(ignore_permissions=True)
		device.db_set({"status": "Error", "last_error": str(exc)[:500]}, update_modified=False)
		frappe.db.commit()
		return {
			"status": "Failed",
			"device": device_name,
			"total_records": 0,
			"new_records": 0,
			"duplicate_records": 0,
			"failed_records": 0,
			"error": str(exc),
			"sync_log": log.name,
		}
