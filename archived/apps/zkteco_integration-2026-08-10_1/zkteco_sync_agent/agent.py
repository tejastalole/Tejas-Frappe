#!/usr/bin/env python3
# Copyright (c) 2026, Exacuer
"""
Exacuer Biometric — Local ZKTeco Sync Agent

Architecture:
  ZKTeco F09 (LAN :4370) → this agent → HTTPS → https://erp.exacuer.com

Cloud ERPNext never dials private device IPs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from erp_client import ErpClient
from queue_db import AttendanceQueue
from zk_client import fetch_device_attendance

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config.json"
DEFAULT_DB = BASE_DIR / "data" / "attendance_queue.db"
DEFAULT_LOG = BASE_DIR / "logs" / "zkteco_agent.log"


def setup_logging(log_path: Path) -> logging.Logger:
	log_path.parent.mkdir(parents=True, exist_ok=True)
	logger = logging.getLogger("zkteco_agent")
	logger.setLevel(logging.INFO)
	fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
	fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
	fh.setFormatter(fmt)
	sh = logging.StreamHandler(sys.stdout)
	sh.setFormatter(fmt)
	logger.handlers.clear()
	logger.addHandler(fh)
	logger.addHandler(sh)
	return logger


def load_config(path: Path) -> dict:
	with open(path, encoding="utf-8") as f:
		cfg = json.load(f)
	if "YOUR_API_KEY" in str(cfg.get("api_key", "")):
		raise SystemExit("Configure api_key / api_secret in config.json (copy from config.example.json)")
	return cfg


def parse_stamp(value: str | None) -> datetime | None:
	if not value:
		return None
	for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
		try:
			return datetime.strptime(value[:19], fmt)
		except ValueError:
			continue
	return None


def map_log_type(punch_status: str, punch: str) -> str | None:
	value = (punch_status or punch or "").strip().upper()
	if value in {"0", "I", "IN", "CHECKIN", "C/IN"}:
		return "IN"
	if value in {"1", "O", "OUT", "CHECKOUT", "C/OUT"}:
		return "OUT"
	return None


class DeviceBackoff:
	def __init__(self):
		self.delays = [5, 10, 30, 60]
		self.index = 0

	def fail(self) -> int:
		delay = self.delays[min(self.index, len(self.delays) - 1)]
		self.index = min(self.index + 1, len(self.delays) - 1)
		return delay

	def reset(self):
		self.index = 0


def sync_device(device: dict, erp: ErpClient, queue: AttendanceQueue, logger: logging.Logger, full_sync: bool = False) -> None:
	name = device["name"]
	ip = device["ip"]
	port = int(device.get("port") or 4370)
	password = int(device.get("password") or 0)
	timeout = int(device.get("timeout") or 5)

	since = None if full_sync else parse_stamp(queue.get_last_att_stamp(name))
	try:
		rows = fetch_device_attendance(ip, port=port, password=password, timeout=timeout, since=since)
	except Exception as exc:
		logger.error("Device Offline / error %s: %s", name, exc)
		try:
			erp.heartbeat(name, status="Offline", last_error=str(exc)[:400])
		except Exception:
			logger.warning("Cloud unavailable while reporting offline status")
		raise

	queued = 0
	max_stamp = since
	for row in rows:
		log_type = map_log_type(row.get("punch_status") or "", row.get("punch") or "")
		ts = row["timestamp"]
		if queue.enqueue(name, row["zkteco_user_id"], ts, log_type, payload=row):
			queued += 1
		dt = parse_stamp(ts)
		if dt and (max_stamp is None or dt > max_stamp):
			max_stamp = dt

	logger.info("Device %s: fetched=%s newly_queued=%s", name, len(rows), queued)

	# Flush queue to cloud (including older pending)
	pending = [r for r in queue.pending(500) if r["device_name"] == name]
	if not pending:
		erp.heartbeat(
			name,
			status="Online",
			last_sync=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
			last_att_stamp=max_stamp.strftime("%Y-%m-%d %H:%M:%S") if max_stamp else None,
		)
		if max_stamp:
			queue.set_last_att_stamp(name, max_stamp.strftime("%Y-%m-%d %H:%M:%S"))
		return

	records = [
		{
			"zkteco_user_id": r["zkteco_user_id"],
			"timestamp": r["timestamp"],
			"log_type": r["log_type"],
		}
		for r in pending
	]

	try:
		result = erp.sync_attendance(name, records)
	except Exception as exc:
		logger.error("Cloud unavailable: %s — keeping %s records in SQLite queue", exc, len(pending))
		for r in pending:
			queue.mark_failed(r["id"], str(exc))
		raise

	# Mark synced / failed based on bulk result (optimistic: mark all synced if no hard fail)
	if result.get("status") in {"success", "partial"} or result.get("created") is not None:
		# Re-check individually for failed mapping rows is expensive; mark all as synced
		# except when total failed == total
		if result.get("failed") and result.get("failed") == result.get("total"):
			for r in pending:
				queue.mark_failed(r["id"], ";".join(result.get("errors") or ["failed"]))
		else:
			for r in pending:
				queue.mark_synced(r["id"])
			logger.info(
				"Sync completed device=%s created=%s duplicate=%s failed=%s",
				name,
				result.get("created"),
				result.get("duplicate"),
				result.get("failed"),
			)
		if max_stamp:
			queue.set_last_att_stamp(name, max_stamp.strftime("%Y-%m-%d %H:%M:%S"))
		erp.heartbeat(
			name,
			status="Online",
			last_sync=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
			last_att_stamp=max_stamp.strftime("%Y-%m-%d %H:%M:%S") if max_stamp else None,
		)
	else:
		for r in pending:
			queue.mark_failed(r["id"], str(result))
		erp.heartbeat(name, status="Error", last_error=str(result)[:400])


def run_loop(config_path: Path):
	cfg = load_config(config_path)
	logger = setup_logging(DEFAULT_LOG)
	queue = AttendanceQueue(DEFAULT_DB)
	erp = ErpClient(cfg["erp_url"], cfg["api_key"], cfg["api_secret"])
	interval = int(cfg.get("sync_interval") or 60)
	full_once = bool(cfg.get("full_sync_on_start"))
	backoffs = {d["name"]: DeviceBackoff() for d in cfg.get("devices") or []}

	logger.info("Exacuer Biometric agent started → %s", cfg["erp_url"])
	logger.info("Devices: %s", ", ".join(d["name"] for d in cfg.get("devices") or []))

	try:
		while True:
			cycle_sleep = interval
			for device in cfg.get("devices") or []:
				name = device["name"]
				try:
					sync_device(device, erp, queue, logger, full_sync=full_once)
					backoffs[name].reset()
				except Exception:
					delay = backoffs[name].fail()
					logger.warning("Backoff %ss for device %s", delay, name)
					cycle_sleep = min(cycle_sleep, delay)
			full_once = False
			time.sleep(cycle_sleep)
	except KeyboardInterrupt:
		logger.info("Agent stopped by user")
	finally:
		queue.close()


def main():
	parser = argparse.ArgumentParser(description="Exacuer ZKTeco Sync Agent")
	parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config.json")
	parser.add_argument("--once", action="store_true", help="Run one sync cycle and exit")
	args = parser.parse_args()
	config_path = Path(args.config)

	if args.once:
		cfg = load_config(config_path)
		logger = setup_logging(DEFAULT_LOG)
		queue = AttendanceQueue(DEFAULT_DB)
		erp = ErpClient(cfg["erp_url"], cfg["api_key"], cfg["api_secret"])
		for device in cfg.get("devices") or []:
			try:
				sync_device(device, erp, queue, logger, full_sync=bool(cfg.get("full_sync_on_start")))
			except Exception as exc:
				logger.error("Sync failed for %s: %s", device.get("name"), exc)
		queue.close()
		return

	run_loop(config_path)


if __name__ == "__main__":
	main()
