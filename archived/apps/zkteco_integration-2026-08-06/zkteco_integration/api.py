# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""
ZKTeco ADMS (Push) protocol handlers.

Device Cloud Server Setting:
  Server Mode  = ADMS
  Server Address = <host>
  Server Port    = 80 / 443 / Nginx ADMS port

Preferred path (via page_renderer):
  http://YOUR_SERVER/iclock/cdata
  http://YOUR_SERVER/iclock/getrequest

Optional whitelist test endpoint:
  /api/method/zkteco_integration.api.iclock
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

import frappe
from werkzeug.wrappers import Response

from zkteco_integration.attendance import process_attendance_rows
from zkteco_integration.parser import parse_attlog


@frappe.whitelist(allow_guest=True)
def iclock() -> str:
	"""
	Simple guest endpoint for smoke tests / Nginx proxy_pass to method URL.

	For full ADMS (/iclock/cdata, /iclock/getrequest), use the page_renderer
	path instead — devices append those suffixes automatically.
	"""
	request = frappe.local.request
	data = request.get_data(as_text=True) or ""
	frappe.logger("zkteco_integration").info(f"iclock payload: {data[:2000]}")

	q = _query(request)
	sn = (q.get("SN") or q.get("sn") or [""])[0].strip()
	table = (q.get("table") or [""])[0].strip().upper()

	if table in {"ATTLOG", "RTLOG"} or "ATTLOG" in data.upper():
		rows = parse_attlog(data)
		if rows:
			process_attendance_rows(rows, serial_number=sn or None)
			frappe.db.commit()

	return "OK"


def handle_request(request, path: str) -> Response:
	"""Route ADMS requests by path suffix (used by page_renderer)."""
	path = (path or "").lstrip("/")
	parts = path.split("/")
	# path like: iclock/cdata | iclock/getrequest | iclock/devicecmd
	endpoint = parts[1] if len(parts) > 1 else ""

	if endpoint == "cdata":
		return _handle_cdata(request)
	if endpoint == "getrequest":
		return _handle_getrequest(request)
	if endpoint in {"devicecmd", "registry"}:
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

	# Handshake / option negotiation
	if request.method == "GET" or options.lower() == "all" or not table:
		return _ok(_handshake_options(sn))

	body = _body_text(request)

	if table in {"ATTLOG", "OPERLOG", "RTLOG"}:
		if table in {"ATTLOG", "RTLOG"} or "ATTLOG" in body.upper():
			rows = parse_attlog(body)
			if rows:
				counts = process_attendance_rows(rows, serial_number=sn)
				frappe.logger("zkteco_integration").info(
					f"ADMS ATTLOG SN={sn} counts={counts}"
				)
		return _ok()

	if table in {"USERINFO", "BIODATA", "OPTIONS"}:
		return _ok()

	# Unknown table — still ACK so device does not retry forever
	return _ok()


def _handle_getrequest(request) -> Response:
	"""Device polls for queued commands. Empty OK = nothing to do."""
	return _ok("OK")


def _handshake_options(sn: str) -> str:
	"""Response body devices expect after options=all."""
	lines = [
		f"GET OPTION FROM: {sn}",
		"Stamp=0",
		"OpStamp=0",
		"ErrorDelay=60",
		"Delay=30",
		"TransTimes=00:00;14:05",
		"TransInterval=1",
		"TransFlag=1111000000",
		"TimeZone=5.5",
		"Realtime=1",
		"Encrypt=0",
	]
	return "\n".join(lines)


@frappe.whitelist()
def test_parse(body: str) -> list[dict[str, Any]]:
	"""Desk helper: parse a sample ATTLOG body without inserting checkins."""
	frappe.only_for(("System Manager", "HR Manager"))
	return parse_attlog(body or "")
