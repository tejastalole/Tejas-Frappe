# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""
ZKTeco ADMS (Push) protocol handler.

Device Cloud Server Setting:
  Server Mode = ADMS
  Server Address = <Frappe host>
  Server Port = 80 / 443 (or site port)

Firmware appends /iclock/* paths automatically.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

import frappe
from frappe.utils import now_datetime
from werkzeug.wrappers import Response

from biometric_integration.sync import process_attendance_rows


def handle_request(request, path: str) -> Response:
	"""Route ADMS requests by path suffix."""
	path = (path or "").lstrip("/")
	parts = path.split("/")
	# path like: iclock/cdata | iclock/getrequest | iclock/devicecmd | iclock/registry
	endpoint = parts[1] if len(parts) > 1 else ""

	if endpoint == "cdata":
		return _handle_cdata(request)
	if endpoint == "getrequest":
		return _handle_getrequest(request)
	if endpoint in {"devicecmd", "registry"}:
		# Acknowledge registration / command results
		_touch_device(_query(request).get("SN", [""])[0])
		return _ok()

	return Response("OK", status=200, mimetype="text/plain")


def _query(request) -> dict[str, list[str]]:
	return parse_qs(request.query_string.decode("utf-8", errors="ignore"), keep_blank_values=True)


def _body_text(request) -> str:
	data = request.get_data(as_text=True) or ""
	return data


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

	# Handshake / option negotiation (GET or options=all)
	if request.method == "GET" or options.lower() == "all" or not table:
		return _ok(_handshake_options(sn, device))

	body = _body_text(request)

	if table in {"ATTLOG", "OPERLOG", "rtlog".upper(), "RTLOG"}:
		# OPERLOG may contain mixed data; ATTLOG / RTLOG are punches
		if table in {"ATTLOG", "RTLOG"} or "ATTLOG" in body.upper():
			rows = parse_attlog(body)
			if rows:
				process_attendance_rows(rows, device_name=device, serial_number=sn, source="ADMS")
				frappe.db.set_single_value("Biometric Settings", "last_push_at", now_datetime())
		return _ok()

	if table in {"USERINFO", "BIODATA", "options".upper(), "OPTIONS"}:
		return _ok()

	# Unknown table — still ACK so device does not retry forever
	return _ok()


def _handle_getrequest(request) -> Response:
	"""Device polls for queued commands. Empty body = nothing to do."""
	q = _query(request)
	sn = (q.get("SN") or [""])[0].strip()
	if sn:
		_touch_device(sn)
	# Return OK with no commands (server→device command queue not implemented yet)
	return _ok("OK")


def _handshake_options(sn: str, device: str | None) -> str:
	"""Response body devices expect after options=all."""
	stamp = "0"
	if device and frappe.db.exists("Biometric Device", device):
		stamp = frappe.db.get_value("Biometric Device", device, "last_att_stamp") or "0"

	# Do not send TimeZone= — SenseFace/eSSL often misreads 5.5/330 and
	# overwrites the device clock (e.g. IST 5:30 → 5:00). Device keeps
	# its own Date/Time; punch times are stored exactly as the device sends.
	lines = [
		f"GET OPTION FROM: {sn}",
		f"Stamp={stamp}",
		"OpStamp=0",
		"ErrorDelay=60",
		"Delay=30",
		"TransTimes=00:00;14:05",
		"TransInterval=1",
		"TransFlag=1111000000",
		"Realtime=1",
		"Encrypt=0",
	]
	return "\n".join(lines)


def _ensure_device(sn: str) -> str | None:
	if not sn:
		return None

	existing = frappe.db.get_value("Biometric Device", {"serial_number": sn}, "name")
	if existing:
		return existing

	# Replace placeholder PENDING-SN on first real ADMS contact
	placeholder = frappe.db.get_value(
		"Biometric Device",
		{"serial_number": "PENDING-SN", "enabled": 1},
		"name",
	)
	if placeholder:
		try:
			frappe.rename_doc("Biometric Device", placeholder, sn, force=True, merge=False)
		except Exception:
			frappe.db.set_value("Biometric Device", placeholder, "serial_number", sn)
			return placeholder
		frappe.db.set_value("Biometric Device", sn, "serial_number", sn)
		return sn

	settings = frappe.get_single("Biometric Settings")
	if not settings.accept_unknown_devices:
		return None

	doc = frappe.get_doc(
		{
			"doctype": "Biometric Device",
			"device_name": sn,
			"serial_number": sn,
			"enabled": 1,
			"connection_mode": "ADMS Push",
			"tcp_port": 4370,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _touch_device(sn: str, device: str | None = None) -> None:
	if not sn:
		return
	name = device or frappe.db.get_value("Biometric Device", {"serial_number": sn}, "name")
	if not name:
		return
	frappe.db.set_value("Biometric Device", name, "last_seen", now_datetime(), update_modified=False)


def parse_attlog(body: str) -> list[dict[str, Any]]:
	"""
	Parse ATTLOG / RTLOG body lines.

	Common formats (tab or space separated):
	  PIN\\tYYYY-MM-DD HH:MM:SS\\tstatus\\tverify\\tworkcode
	  PIN=1\\tDateTime=2026-08-01 09:01:10\\tStatus=0\\tVerified=1
	"""
	rows: list[dict[str, Any]] = []
	if not body:
		return rows

	for raw_line in body.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
		line = raw_line.strip()
		if not line:
			continue

		parsed = _parse_attlog_line(line)
		if parsed:
			parsed["raw_line"] = line
			rows.append(parsed)

	return rows


def _parse_attlog_line(line: str) -> dict[str, Any] | None:
	# key=value style
	if "=" in line and ("PIN=" in line.upper() or "DATETIME=" in line.upper().replace(" ", "")):
		parts = {}
		for token in line.replace(",", "\t").split("\t"):
			token = token.strip()
			if "=" not in token:
				continue
			k, v = token.split("=", 1)
			parts[k.strip().upper()] = v.strip()

		user_id = parts.get("PIN") or parts.get("USERID") or parts.get("EMP_CODE")
		punch_time = parts.get("DATETIME") or parts.get("TIME") or parts.get("CHECKTIME")
		if not user_id or not punch_time:
			return None
		return {
			"user_id": str(user_id).strip(),
			"punch_time": punch_time,
			"punch_status": parts.get("STATUS") or parts.get("CHECKTYPE") or "",
			"verify_mode": parts.get("VERIFIED") or parts.get("VERIFY") or "",
		}

	# tab / multi-space positional
	cols = [c for c in line.split("\t") if c != ""]
	if len(cols) < 2:
		cols = line.split()

	if len(cols) < 2:
		return None

	user_id = cols[0].strip()
	punch_time = cols[1].strip()
	# Sometimes datetime is split across two columns
	if len(cols) >= 3 and ":" in cols[2] and "-" not in cols[1]:
		punch_time = f"{cols[1]} {cols[2]}"
		status = cols[3] if len(cols) > 3 else ""
		verify = cols[4] if len(cols) > 4 else ""
	else:
		status = cols[2] if len(cols) > 2 else ""
		verify = cols[3] if len(cols) > 3 else ""

	if not user_id or not punch_time:
		return None

	return {
		"user_id": user_id,
		"punch_time": punch_time,
		"punch_status": status,
		"verify_mode": verify,
	}
