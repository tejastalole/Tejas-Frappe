# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

"""ZKTeco TCP client using pyzk. For LAN use only (local agent or on-prem site)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import now_datetime


def _get_password(device) -> int | None:
	try:
		raw = device.get_password("password") if hasattr(device, "get_password") else device.password
		if raw in (None, ""):
			return 0
		return int(raw)
	except Exception:
		return 0


def connect_device(device) -> Any:
	"""Return connected ZK instance. Caller must disconnect."""
	try:
		from zk import ZK
	except ImportError as exc:
		raise RuntimeError("pyzk is not installed. Run: bench pip install pyzk") from exc

	zk = ZK(
		device.ip_address,
		port=int(device.tcp_port or 4370),
		timeout=int(device.timeout or 5),
		password=_get_password(device) or 0,
		force_udp=False,
		ommit_ping=False,
	)
	return zk.connect()


def safe_disconnect(conn) -> None:
	if not conn:
		return
	try:
		conn.disconnect()
	except Exception:
		pass


def test_device_connection(device_name: str) -> dict[str, Any]:
	device = frappe.get_doc("ZKTeco Device", device_name)
	conn = None
	try:
		conn = connect_device(device)
		info = {
			"firmware": _safe(conn.get_firmware_version),
			"serial": _safe(conn.get_serialnumber),
			"platform": _safe(conn.get_platform),
			"device_name": _safe(conn.get_device_name),
		}
		device.db_set(
			{
				"status": "Online",
				"last_seen": now_datetime(),
				"last_error": None,
			},
			update_modified=False,
		)
		details = "<br>".join(f"{k}: {v}" for k, v in info.items() if v)
		return {
			"success": True,
			"device_info": info.get("device_name") or info.get("serial") or device.device_name,
			"details": details,
			"info": info,
		}
	except Exception as exc:
		device.db_set(
			{
				"status": "Error",
				"last_error": str(exc)[:500],
			},
			update_modified=False,
		)
		frappe.log_error(title=f"ZKTeco Connection Error ({device_name})", message=frappe.get_traceback())
		return {"success": False, "error": str(exc)}
	finally:
		safe_disconnect(conn)


def fetch_attendance(device_name: str, since=None) -> list[dict[str, Any]]:
	"""Download attendance rows from device. Optional since datetime filter."""
	device = frappe.get_doc("ZKTeco Device", device_name)
	conn = None
	rows: list[dict[str, Any]] = []
	try:
		conn = connect_device(device)
		device.db_set({"status": "Online", "last_seen": now_datetime(), "last_error": None}, update_modified=False)
		for att in conn.get_attendance() or []:
			user_id = str(getattr(att, "user_id", None) or getattr(att, "uid", "") or "").strip()
			punch_time = getattr(att, "timestamp", None)
			if not user_id or not punch_time:
				continue
			if since and punch_time <= since:
				continue
			status = getattr(att, "status", None)
			punch = getattr(att, "punch", None)
			rows.append(
				{
					"zkteco_user_id": user_id,
					"timestamp": punch_time,
					"punch_status": str(status if status is not None else ""),
					"punch": str(punch if punch is not None else ""),
				}
			)
		return rows
	except Exception:
		device.db_set(
			{"status": "Error", "last_error": frappe.get_traceback()[:1000]},
			update_modified=False,
		)
		frappe.log_error(title=f"ZKTeco Fetch Error ({device_name})", message=frappe.get_traceback())
		raise
	finally:
		safe_disconnect(conn)


def _safe(fn):
	try:
		return fn()
	except Exception:
		return None
