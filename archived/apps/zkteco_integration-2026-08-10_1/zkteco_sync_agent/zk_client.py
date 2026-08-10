# Copyright (c) 2026, Exacuer
"""Pull attendance from ZKTeco via pyzk."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger("zkteco_agent")


def fetch_device_attendance(
	ip: str,
	port: int = 4370,
	password: int = 0,
	timeout: int = 5,
	since: datetime | None = None,
) -> list[dict[str, Any]]:
	try:
		from zk import ZK
	except ImportError as exc:
		raise RuntimeError("pyzk is not installed. pip install pyzk") from exc

	conn = None
	rows: list[dict[str, Any]] = []
	try:
		zk = ZK(ip, port=int(port), timeout=int(timeout), password=int(password or 0), force_udp=False)
		conn = zk.connect()
		logger.info("Connected to %s:%s", ip, port)
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
					"timestamp": punch_time.strftime("%Y-%m-%d %H:%M:%S")
					if isinstance(punch_time, datetime)
					else str(punch_time),
					"punch_status": str(status if status is not None else ""),
					"punch": str(punch if punch is not None else ""),
					"_dt": punch_time if isinstance(punch_time, datetime) else None,
				}
			)
		rows.sort(key=lambda r: r.get("_dt") or r["timestamp"])
		for r in rows:
			r.pop("_dt", None)
		logger.info("Retrieved %s attendance records from %s", len(rows), ip)
		return rows
	finally:
		if conn:
			try:
				conn.disconnect()
			except Exception:
				pass
