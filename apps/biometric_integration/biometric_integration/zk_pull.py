# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Optional TCP pull from ZKTeco devices on port 4370 (pyzk)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import now_datetime

from biometric_integration.sync import process_attendance_rows


def test_connection(device_name: str) -> dict[str, Any]:
	device = frappe.get_doc("Biometric Device", device_name)
	if not device.ip_address:
		return {"success": False, "error": "IP Address is not set"}

	try:
		from zk import ZK
	except ImportError:
		return {
			"success": False,
			"error": "pyzk is not installed. Run: bench pip install pyzk",
		}

	conn = None
	try:
		zk = ZK(device.ip_address, port=int(device.tcp_port or 4370), timeout=10)
		conn = zk.connect()
		info = {
			"firmware": _safe(conn.get_firmware_version),
			"serial": _safe(conn.get_serialnumber),
			"platform": _safe(conn.get_platform),
			"device_name": _safe(conn.get_device_name),
		}
		# Persist discovered SN / firmware when available
		updates = {}
		if info.get("serial") and device.serial_number in {None, "", "PENDING-SN"}:
			updates["serial_number"] = info["serial"]
		if info.get("firmware"):
			updates["firmware_version"] = info["firmware"]
		if info.get("platform"):
			updates["platform"] = info["platform"]
		if updates:
			frappe.db.set_value("Biometric Device", device.name, updates)
		return {"success": True, "device_info": info}
	except Exception as exc:
		return {"success": False, "error": str(exc)}
	finally:
		if conn:
			try:
				conn.disconnect()
			except Exception:
				pass


def pull_device(device_name: str) -> dict[str, int]:
	device = frappe.get_doc("Biometric Device", device_name)
	_validate_tcp_device(device)

	sync_log = frappe.get_doc(
		{
			"doctype": "Biometric Sync Log",
			"status": "Running",
			"source": "TCP Pull",
			"started_at": now_datetime(),
			"device": device.name,
			"serial_number": device.serial_number,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	try:
		rows = _fetch_attendance(device)
		counts = process_attendance_rows(
			rows,
			device_name=device.name,
			serial_number=device.serial_number,
			source="TCP Pull",
		)
		status = "Success"
		if counts["errors"] and counts["inserted"]:
			status = "Partial"
		elif counts["errors"] and not counts["inserted"]:
			status = "Failed"

		sync_log.status = status
		sync_log.downloaded = counts["downloaded"]
		sync_log.inserted = counts["inserted"]
		sync_log.skipped = counts["skipped"]
		sync_log.errors = counts["errors"]
		sync_log.ended_at = now_datetime()
		sync_log.save(ignore_permissions=True)
		frappe.db.commit()
		return counts
	except frappe.ValidationError:
		sync_log.status = "Failed"
		sync_log.error_details = frappe.get_traceback()
		sync_log.ended_at = now_datetime()
		sync_log.errors = 1
		sync_log.save(ignore_permissions=True)
		frappe.db.commit()
		raise
	except Exception as exc:
		sync_log.status = "Failed"
		sync_log.error_details = frappe.get_traceback()
		sync_log.ended_at = now_datetime()
		sync_log.errors = 1
		sync_log.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.log_error(title=f"TCP Pull Failed ({device.name})", message=sync_log.error_details)
		frappe.throw(_tcp_error_message(device, exc), title="TCP Pull Failed")


def pull_all_enabled() -> dict[str, int]:
	totals = {"downloaded": 0, "inserted": 0, "skipped": 0, "errors": 0, "devices": 0}
	devices = frappe.get_all(
		"Biometric Device",
		filters={
			"enabled": 1,
			"connection_mode": ("in", ["TCP Pull", "Both"]),
			"ip_address": ("is", "set"),
		},
		pluck="name",
	)
	for name in devices:
		try:
			counts = pull_device(name)
			totals["downloaded"] += counts.get("downloaded", 0)
			totals["inserted"] += counts.get("inserted", 0)
			totals["skipped"] += counts.get("skipped", 0)
			totals["errors"] += counts.get("errors", 0)
			totals["devices"] += 1
		except Exception:
			totals["errors"] += 1

	frappe.db.set_single_value("Biometric Settings", "last_pull_at", now_datetime())
	frappe.db.commit()
	return totals


def _validate_tcp_device(device) -> None:
	if not device.ip_address:
		frappe.throw("Set IP Address on the Biometric Device before TCP pull.")
	if device.connection_mode == "ADMS Push":
		frappe.throw(
			(
				"This device is set to <b>ADMS Push</b>. "
				"SenseFace should push punches to <code>/iclock/*</code> — do not use TCP Pull.<br><br>"
				"On the device: Cloud Server → ADMS → Server Address = your PC IP, Port = <b>8007</b>.<br>"
				"Only use Pull Attendance if Connection Mode is <b>TCP Pull</b> or <b>Both</b> "
				"and port 4370 is open on the device."
			),
			title="Use ADMS Push instead",
		)


def _tcp_error_message(device, exc: Exception) -> str:
	host = f"{device.ip_address}:{int(device.tcp_port or 4370)}"
	err = str(exc)
	return (
		f"Cannot open ZK TCP session to <b>{frappe.utils.escape_html(host)}</b>.<br>"
		f"<code>{frappe.utils.escape_html(err)}</code><br><br>"
		"From this bench (WSL), port 4370 must accept connections. "
		"SenseFace often keeps 4370 closed and only supports <b>ADMS push</b>. "
		"Prefer Connection Mode = ADMS Push and point the device Cloud Server to Frappe."
	)


def _fetch_attendance(device) -> list[dict[str, Any]]:
	try:
		from zk import ZK
	except ImportError:
		frappe.throw("pyzk is not installed. Run: bench pip install pyzk")

	conn = None
	rows: list[dict[str, Any]] = []
	try:
		zk = ZK(device.ip_address, port=int(device.tcp_port or 4370), timeout=15)
		conn = zk.connect()
		for att in conn.get_attendance() or []:
			user_id = str(getattr(att, "user_id", None) or getattr(att, "uid", "") or "").strip()
			punch_time = getattr(att, "timestamp", None)
			if not user_id or not punch_time:
				continue
			status = getattr(att, "status", None)
			punch = getattr(att, "punch", None)
			rows.append(
				{
					"user_id": user_id,
					"punch_time": punch_time,
					"punch_status": str(status if status is not None else punch or ""),
					"verify_mode": str(getattr(att, "punch", "") or ""),
					"raw_line": f"TCP:{user_id}|{punch_time}|{status}",
				}
			)
	except Exception as exc:
		frappe.throw(_tcp_error_message(device, exc), title="TCP Pull Failed")
	finally:
		if conn:
			try:
				conn.disconnect()
			except Exception:
				pass
	return rows


def _safe(fn):
	try:
		return fn()
	except Exception:
		return None
