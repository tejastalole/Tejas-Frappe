# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Parse ZKTeco ADMS ATTLOG / RTLOG punch payloads."""

from __future__ import annotations

from typing import Any


def parse_attlog(body: str) -> list[dict[str, Any]]:
	"""
	Parse ATTLOG / RTLOG body lines into punch dicts.

	Common formats:
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
		parts: dict[str, str] = {}
		for token in line.replace(",", "\t").split("\t"):
			token = token.strip()
			if "=" not in token:
				continue
			key, value = token.split("=", 1)
			parts[key.strip().upper()] = value.strip()

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

	# Sometimes date and time are split across two columns
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
