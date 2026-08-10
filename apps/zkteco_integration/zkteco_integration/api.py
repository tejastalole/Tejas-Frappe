# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""
ZKTeco ADMS handlers for SenseFace 2A.

Device Cloud Server Setting example:
  Server Mode    = ADMS
  Server Address = 192.168.1.10   (your Frappe / Nginx host)
  Server Port    = 8081          (Nginx) or 8007 (direct bench)

Firmware appends /iclock/cdata and /iclock/getrequest automatically.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

import frappe
from frappe.utils import cint, now_datetime
from werkzeug.wrappers import Response

from zkteco_integration.attendance import process_attendance_rows
from zkteco_integration.parser import parse_attlog


# IST = UTC+5:30 → 330 minutes (ZK ADMS expects minutes, not 5.5)
IST_OFFSET_MINUTES = 330


@frappe.whitelist(allow_guest=True)
def iclock() -> str:
	"""Smoke-test / Nginx proxy endpoint. Prefer /iclock/* for real devices."""
	request = frappe.local.request
	data = request.get_data(as_text=True) or ""
	frappe.logger("zkteco_integration").info(f"iclock payload: {data[:2000]}")

	q = _query(request)
	sn = (q.get("SN") or q.get("sn") or [""])[0].strip()
	table = (q.get("table") or [""])[0].strip().upper()

	if table in {"ATTLOG", "RTLOG"} or "ATTLOG" in data.upper():
		device = _ensure_device(sn) if sn else None
		rows = parse_attlog(data)
		if rows:
			process_attendance_rows(rows, serial_number=sn or None, device_name=device)
			frappe.db.commit()

	return "OK"


def handle_request(request, path: str) -> Response:
	"""Route ADMS requests by path suffix (used by page_renderer)."""
	path = (path or "").lstrip("/")
	parts = path.split("/")
	endpoint = parts[1] if len(parts) > 1 else ""

	if endpoint == "cdata":
		return _handle_cdata(request)
	if endpoint == "getrequest":
		return _handle_getrequest(request)
	if endpoint in {"devicecmd", "registry"}:
		sn = (_query(request).get("SN") or [""])[0].strip()
		if sn:
			_touch_device(sn)
		return _ok()

	return _ok()


def _query(request) -> dict[str, list[str]]:
	return parse_qs(request.query_string.decode("utf-8", errors="ignore"), keep_blank_values=True)


def _body_text(request) -> str:
	return request.get_data(as_text=True) or ""


def _ok(body: str = "OK") -> Response:
	return Response(body, status=200, mimetype="text/plain")


def _handle_cdata(request) -> Response:
	q = _query(request)
	sn = (q.get("SN") or q.get("sn") or [""])[0].strip()
	table = (q.get("table") or [""])[0].strip().upper()
	options = (q.get("options") or [""])[0]

	if not sn:
		return Response("Missing SN", status=400, mimetype="text/plain")

	device = _ensure_device(sn)
	_touch_device(sn, device=device)

	if request.method == "GET" or options.lower() == "all" or not table:
		return _ok(_handshake_options(sn, device))

	body = _body_text(request)

	if table in {"ATTLOG", "OPERLOG", "RTLOG"}:
		if table in {"ATTLOG", "RTLOG"} or "ATTLOG" in body.upper():
			rows = parse_attlog(body)
			if rows:
				counts = process_attendance_rows(rows, serial_number=sn, device_name=device)
				frappe.logger("zkteco_integration").info(f"ADMS ATTLOG SN={sn} counts={counts}")
		return _ok()

	if table in {"USERINFO", "BIODATA", "OPTIONS"}:
		return _ok()

	return _ok()


def _handle_getrequest(request) -> Response:
	"""Device polls for commands — sync clock at most once per 30 minutes."""
	q = _query(request)
	sn = (q.get("SN") or [""])[0].strip()
	if sn:
		_touch_device(sn)

	cache_key = f"zkteco_last_set_time:{sn or 'unknown'}"
	if sn and not frappe.cache.get_value(cache_key):
		cmd_id = cint(frappe.cache.get_value("zkteco_cmd_id") or 0) + 1
		frappe.cache.set_value("zkteco_cmd_id", cmd_id, expires_in_sec=86400)
		frappe.cache.set_value(cache_key, 1, expires_in_sec=1800)
		server_time = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
		# SenseFace may accept either form
		return _ok(
			f"C:{cmd_id}:SET TIME {server_time}\n"
			f"C:{cmd_id + 1}:SET OPTIONS DateTime={server_time},TimeZone={IST_OFFSET_MINUTES}"
		)

	return _ok("OK")


def _handshake_options(sn: str, device: str | None) -> str:
	stamp = "0"
	if device and frappe.db.exists("ZKTeco Device", device):
		stamp = frappe.db.get_value("ZKTeco Device", device, "last_att_stamp") or "0"

	server_time = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
	lines = [
		f"GET OPTION FROM: {sn}",
		f"Stamp={stamp}",
		"OpStamp=0",
		"ErrorDelay=60",
		"Delay=30",
		"TransTimes=00:00;14:05",
		"TransInterval=1",
		"TransFlag=1111000000",
		f"TimeZone={IST_OFFSET_MINUTES}",
		f"DateTime={server_time}",
		"SyncTime=60",
		"Realtime=1",
		"Encrypt=0",
	]
	return "\n".join(lines)


def _ensure_device(sn: str) -> str | None:
	if not sn:
		return None

	existing = frappe.db.get_value("ZKTeco Device", {"serial_number": sn}, "name")
	if existing:
		return existing

	settings = frappe.get_single("ZKTeco Settings")
	if not settings.accept_unknown_devices:
		frappe.logger("zkteco_integration").warning(f"Unknown device SN={sn} rejected")
		return None

	doc = frappe.get_doc(
		{
			"doctype": "ZKTeco Device",
			"device_name": sn,
			"serial_number": sn,
			"enabled": 1,
			"device_id": 1,
			"tcp_port": 4370,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _touch_device(sn: str, device: str | None = None) -> None:
	if not sn:
		return
	name = device or frappe.db.get_value("ZKTeco Device", {"serial_number": sn}, "name")
	if not name:
		return
	frappe.db.set_value("ZKTeco Device", name, "last_seen", now_datetime(), update_modified=False)


@frappe.whitelist()
def test_parse(body: str) -> list[dict[str, Any]]:
	frappe.only_for(("System Manager", "HR Manager"))
	return parse_attlog(body or "")
