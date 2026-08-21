# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Binance trade WebSocket streamer → Frappe cache + realtime."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import frappe

CACHE_KEY = "currencyinfo:last_trade"
STREAM_FLAG = "currencyinfo:stream_running"
STOP_FLAG = "currencyinfo:stream_stop"
JOB_ID = "currencyinfo_binance_stream"
REALTIME_EVENT = "currencyinfo_trade"


def _get_settings() -> dict:
	row = frappe.db.get_singles_dict("Currency Info Settings") or {}
	return {
		"enabled": int(row.get("enabled") or 0),
		"symbol": (row.get("symbol") or "BTCUSDT").upper(),
		"stream_url": row.get("stream_url")
		or "wss://stream.binance.com:9443/ws/btcusdt@trade",
	}


def get_stream_url(settings: dict | None = None) -> str:
	settings = settings or _get_settings()
	url = (settings.get("stream_url") or "").strip()
	if url:
		return url
	symbol = (settings.get("symbol") or "BTCUSDT").lower()
	return f"wss://stream.binance.com:9443/ws/{symbol}@trade"


def parse_trade(payload: dict) -> dict:
	"""Map Binance trade payload to a normalized tick."""
	price = float(payload.get("p") or 0)
	qty = float(payload.get("q") or 0)
	is_buyer_maker = bool(payload.get("m"))
	side = "Sell" if is_buyer_maker else "Buy"
	trade_ms = int(payload.get("T") or payload.get("E") or 0)
	trade_time = (
		datetime.fromtimestamp(trade_ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
		if trade_ms
		else None
	)
	return {
		"symbol": payload.get("s") or "",
		"trade_id": str(payload.get("t") or ""),
		"price": price,
		"quantity": qty,
		"quote_qty": round(price * qty, 8),
		"side": side,
		"is_buyer_maker": is_buyer_maker,
		"trade_time": str(trade_time) if trade_time else None,
		"event_time": payload.get("E"),
	}


@frappe.whitelist()
def get_latest_trade() -> dict | None:
	cached = frappe.cache().get_value(CACHE_KEY)
	if cached:
		return cached
	row = frappe.db.get_singles_dict("Currency Info Settings") or {}
	if not row.get("last_price"):
		return None
	return {
		"symbol": row.get("symbol") or "BTCUSDT",
		"trade_id": row.get("last_trade_id") or "",
		"price": float(row.get("last_price") or 0),
		"quantity": float(row.get("last_quantity") or 0),
		"side": row.get("last_side") or "",
		"trade_time": str(row.get("last_trade_time") or ""),
		"connection_status": row.get("connection_status") or "",
	}


@frappe.whitelist()
def get_client_config() -> dict:
	settings = _get_settings()
	return {
		"enabled": settings["enabled"],
		"symbol": settings["symbol"],
		"stream_url": get_stream_url(settings),
		"realtime_event": REALTIME_EVENT,
		"latest": get_latest_trade(),
	}


@frappe.whitelist()
def restart_stream() -> dict:
	frappe.cache().set_value(STOP_FLAG, 1)
	frappe.cache().set_value(STREAM_FLAG, 0)
	ensure_stream_loop(force=True)
	return {"ok": True}


def scheduled_watchdog():
	"""Minute cron — keep stream job alive if enabled."""
	try:
		ensure_stream_loop(force=False)
	except Exception:
		frappe.log_error(title="Currency Info watchdog", message=frappe.get_traceback())


def ensure_stream_loop(force: bool = False):
	settings = _get_settings()
	if not settings["enabled"]:
		frappe.cache().set_value(STOP_FLAG, 1)
		frappe.cache().set_value(STREAM_FLAG, 0)
		_set_connection_status("Stopped")
		return

	running = int(frappe.cache().get_value(STREAM_FLAG) or 0)
	if running and not force:
		return

	frappe.cache().set_value(STOP_FLAG, 0)
	frappe.enqueue(
		"currencyinfo.currency_info.stream.run_stream_job",
		queue="long",
		timeout=60 * 30,  # 30 minutes then watchdog requeues
		job_name=JOB_ID,
		deduplicate=True,
		enqueue_after_commit=False,
	)


def _set_connection_status(status: str):
	try:
		frappe.db.set_single_value("Currency Info Settings", "connection_status", status)
		frappe.db.commit()
	except Exception:
		pass


def _persist_tick(tick: dict, trades_received: int):
	frappe.cache().set_value(CACHE_KEY, tick, expires_in_sec=3600)
	try:
		frappe.publish_realtime(REALTIME_EVENT, tick, after_commit=False)
	except Exception:
		pass

	last_db = frappe.cache().get_value("currencyinfo:last_db_write") or 0
	now = time.time()
	if now - float(last_db) < 2:
		return
	frappe.cache().set_value("currencyinfo:last_db_write", now)

	values = {
		"last_price": tick["price"],
		"last_quantity": tick["quantity"],
		"last_side": tick["side"],
		"last_trade_time": tick["trade_time"],
		"last_trade_id": tick["trade_id"],
		"trades_received": trades_received,
		"connection_status": "Connected",
	}
	for field, value in values.items():
		frappe.db.set_single_value(
			"Currency Info Settings",
			field,
			value,
			update_modified=False,
		)
	frappe.db.commit()


def run_stream_job():
	"""Long RQ job: stay connected to Binance and push ticks."""
	try:
		import websocket
	except ImportError:
		_set_connection_status("Missing websocket-client")
		frappe.log_error(
			title="Currency Info missing dependency",
			message="Install websocket-client: bench pip install websocket-client",
		)
		return

	frappe.cache().set_value(STREAM_FLAG, 1)
	frappe.cache().set_value(STOP_FLAG, 0)
	started = time.time()
	max_runtime = 60 * 25  # leave headroom under 30m job timeout
	trades = int(frappe.db.get_single_value("Currency Info Settings", "trades_received") or 0)
	backoff = 1

	try:
		while not int(frappe.cache().get_value(STOP_FLAG) or 0):
			if time.time() - started > max_runtime:
				break

			settings = _get_settings()
			if not settings["enabled"]:
				_set_connection_status("Stopped")
				break

			url = get_stream_url(settings)
			_set_connection_status("Connecting")

			try:
				ws = websocket.create_connection(url, timeout=20)
				_set_connection_status("Connected")
				backoff = 1

				while not int(frappe.cache().get_value(STOP_FLAG) or 0):
					if time.time() - started > max_runtime:
						break
					ws.settimeout(5)
					try:
						raw = ws.recv()
					except Exception:
						continue

					if not raw:
						break

					try:
						payload = json.loads(raw)
					except Exception:
						continue

					if payload.get("e") != "trade":
						continue

					tick = parse_trade(payload)
					trades += 1
					_persist_tick(tick, trades)

				try:
					ws.close()
				except Exception:
					pass

			except Exception as exc:
				_set_connection_status(f"Reconnect ({exc.__class__.__name__})")
				time.sleep(backoff)
				backoff = min(backoff * 2, 30)
				continue

			time.sleep(backoff)
			backoff = min(backoff * 2, 30)
	finally:
		frappe.cache().set_value(STREAM_FLAG, 0)
		# Requeue if still enabled
		if _get_settings()["enabled"] and not int(frappe.cache().get_value(STOP_FLAG) or 0):
			frappe.enqueue(
				"currencyinfo.currency_info.stream.run_stream_job",
				queue="long",
				timeout=60 * 30,
				job_name=JOB_ID,
				deduplicate=True,
			)
