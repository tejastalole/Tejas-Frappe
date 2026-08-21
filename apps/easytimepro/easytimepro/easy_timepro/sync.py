# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Sync Easy TimePro biometric transactions into Frappe DocTypes."""

from __future__ import annotations

import json

import frappe
from frappe.utils import get_datetime, now_datetime

from easytimepro.easy_timepro.api_client import EasyTimeProClient


PUNCH_STATE_MAP = {
	"0": "IN",
	"1": "OUT",
	"2": "OUT",  # Break Out
	"3": "IN",  # Break In
	"4": "IN",  # Overtime In
	"5": "OUT",  # Overtime Out
	"255": "IN",  # No status / undefined (ZKTeco) — treat as Check In
	"Check In": "IN",
	"Check Out": "OUT",
	"I": "IN",
	"O": "OUT",
}


def map_log_type(punch_state) -> str:
	key = str(punch_state).strip() if punch_state is not None else ""
	return PUNCH_STATE_MAP.get(key, "Unknown")


def resolve_log_type(punch_state, employee: str | None = None) -> str:
	"""
	Map Easy TimePro punch_state to IN/OUT for Employee Checkin.

	State 255 (No Status) defaults to IN. If still unknown and employee is known,
	alternate from the employee's last checkin.
	"""
	mapped = map_log_type(punch_state)
	if mapped in ("IN", "OUT"):
		return mapped

	if employee:
		last = frappe.db.get_value(
			"Employee Checkin",
			{"employee": employee},
			"log_type",
			order_by="time desc",
		)
		if last == "IN":
			return "OUT"
		return "IN"

	# Safe default when device sends no status
	return "IN"

def _normalize_person_name(name: str) -> str:
	return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def find_employee(employee_id: str) -> str | None:
	"""Map Easy TimePro Employee ID (emp_code) → Frappe Employee via attendance_device_id."""
	if not employee_id:
		return None
	employee_id = str(employee_id).strip()

	# Primary: Attendance Device ID must equal Easy TimePro Employee ID
	name = frappe.db.get_value(
		"Employee",
		{"attendance_device_id": employee_id, "status": "Active"},
		"name",
	)
	if name:
		return name

	name = frappe.db.get_value("Employee", {"attendance_device_id": employee_id}, "name")
	if name:
		return name

	# Fallbacks
	name = frappe.db.get_value("Employee", {"employee_number": employee_id}, "name")
	if name:
		return name
	return frappe.db.get_value("Employee", {"name": employee_id}, "name")


def sync_employee_device_ids_from_easytimepro() -> dict:
	"""
	Set Employee.attendance_device_id from Easy TimePro Employee ID by matching names.
	Easy TimePro Employee ID 1 = Tejas, etc.
	"""
	client = EasyTimeProClient.from_settings()
	payload = client.get("/personnel/api/employees/", {"page": 1, "page_size": 200})
	etp_rows = payload.get("data") or []

	employees = frappe.get_all(
		"Employee",
		fields=["name", "employee_name", "attendance_device_id", "status"],
		filters={"status": "Active"},
	)
	by_norm_name = {}
	for emp in employees:
		key = _normalize_person_name(emp.employee_name)
		if key:
			by_norm_name.setdefault(key, []).append(emp)

	updated = []
	unmatched = []
	conflicts = []

	for row in etp_rows:
		etp_id = str(row.get("emp_code") or "").strip()
		first = (row.get("first_name") or "").strip()
		last = (row.get("last_name") or "").strip()
		full = f"{first} {last}".strip() or first
		if not etp_id or not full:
			continue

		norm = _normalize_person_name(full)
		# Also try first-name-only match (ETP often has single token names)
		candidates = by_norm_name.get(norm) or []
		if not candidates:
			first_norm = _normalize_person_name(first)
			for emp in employees:
				emp_norm = _normalize_person_name(emp.employee_name)
				if first_norm and (emp_norm.startswith(first_norm) or first_norm in emp_norm):
					candidates.append(emp)

		# Deduplicate candidates
		seen = set()
		uniq = []
		for emp in candidates:
			if emp.name not in seen:
				seen.add(emp.name)
				uniq.append(emp)
		candidates = uniq

		if len(candidates) != 1:
			unmatched.append({"etp_id": etp_id, "etp_name": full, "matches": [c.name for c in candidates]})
			continue

		emp = candidates[0]
		# Ensure no other employee already owns this device id (unique field; use NULL not "")
		owners = frappe.get_all(
			"Employee",
			filters={"attendance_device_id": etp_id, "name": ["!=", emp.name]},
			pluck="name",
		)
		for owner_name in owners:
			frappe.db.sql(
				"update `tabEmployee` set attendance_device_id=null where name=%s",
				owner_name,
			)
			conflicts.append({"cleared_from": owner_name, "etp_id": etp_id})

		if emp.attendance_device_id != etp_id:
			frappe.db.set_value("Employee", emp.name, "attendance_device_id", etp_id, update_modified=False)
			updated.append({"employee": emp.name, "name": emp.employee_name, "employee_id": etp_id})
			emp.attendance_device_id = etp_id

	frappe.db.commit()
	return {
		"updated": updated,
		"unmatched": unmatched,
		"conflicts_cleared": conflicts,
		"etp_employees": len(etp_rows),
	}


def remap_punch_log_employees() -> dict:
	"""Re-link punch logs + checkins using current attendance_device_id mapping."""
	fixed = 0
	checkins_fixed = 0
	for row in frappe.get_all(
		"Easy TimePro Punch Log",
		fields=["name", "emp_code", "employee", "employee_name", "employee_checkin", "punch_time", "log_type"],
	):
		correct = find_employee(row.emp_code)
		if not correct:
			continue

		correct_name = frappe.db.get_value("Employee", correct, "employee_name")
		needs_update = correct != row.employee or row.employee_name != correct_name
		if needs_update:
			frappe.db.set_value(
				"Easy TimePro Punch Log",
				row.name,
				{"employee": correct, "employee_name": correct_name},
				update_modified=False,
			)
			fixed += 1
			if row.employee_checkin and frappe.db.exists("Employee Checkin", row.employee_checkin):
				frappe.db.set_value(
					"Employee Checkin",
					row.employee_checkin,
					"employee",
					correct,
					update_modified=False,
				)
				checkins_fixed += 1

	frappe.db.commit()
	return {"punch_logs_updated": fixed, "employee_checkins_updated": checkins_fixed}

def sync_transactions(force: bool = False) -> dict:
	settings = frappe.get_single("Easy TimePro Settings")
	if not settings.enabled and not force:
		return {"fetched": 0, "created": 0, "skipped": 0, "message": "Sync disabled"}

	client = EasyTimeProClient.from_settings()
	min_id = int(settings.last_transaction_id or 0)

	# After punch logs are cleared, the cursor must restart or nothing re-imports.
	if not frappe.db.count("Easy TimePro Punch Log"):
		min_id = 0

	fetched = 0
	created = 0
	skipped = 0
	max_id = min_id
	errors = []

	try:
		for row in client.iter_transactions(min_id=min_id if min_id else None, page_size=100):
			fetched += 1
			tx_id = int(row.get("id") or 0)
			max_id = max(max_id, tx_id)

			if frappe.db.exists("Easy TimePro Punch Log", {"transaction_id": tx_id}):
				skipped += 1
				continue

			emp_code = str(row.get("emp_code") or "").strip()  # Easy TimePro Employee ID
			punch_time = row.get("punch_time")
			if not emp_code or not punch_time:
				skipped += 1
				continue

			employee = find_employee(emp_code)
			log_type = resolve_log_type(row.get("punch_state"), employee)

			doc = frappe.get_doc(
				{
					"doctype": "Easy TimePro Punch Log",
					"transaction_id": tx_id,
					"emp_code": emp_code,
					"employee": employee,
					"punch_time": get_datetime(punch_time),
					"log_type": log_type,
					"punch_state": str(row.get("punch_state") if row.get("punch_state") is not None else ""),
					"terminal_sn": row.get("terminal_sn"),
					"terminal_alias": row.get("terminal_alias"),
					"area_alias": row.get("area_alias"),
					"verify_type": str(row.get("verify_type") if row.get("verify_type") is not None else ""),
					"source": "Easy TimePro",
					"raw_json": json.dumps(row, default=str),
				}
			)
			doc.insert(ignore_permissions=True)
			created += 1

			if settings.create_employee_checkin and employee and log_type in ("IN", "OUT"):
				try:
					checkin_name = create_employee_checkin(doc)
					if checkin_name:
						frappe.db.set_value(
							"Easy TimePro Punch Log",
							doc.name,
							"employee_checkin",
							checkin_name,
							update_modified=False,
						)
				except Exception as exc:
					errors.append(f"{emp_code}@{punch_time}: {exc}")

		message = f"Fetched {fetched}, created {created}, skipped {skipped}"
		if errors:
			message += f". Checkin errors: {len(errors)}"

		settings.db_set(
			{
				"last_sync_on": now_datetime(),
				"last_sync_status": "Partial" if errors else "Success",
				"last_sync_message": message[:140],
				"last_transaction_id": max_id,
			},
			update_modified=True,
		)
		frappe.db.commit()
		return {
			"fetched": fetched,
			"created": created,
			"skipped": skipped,
			"last_transaction_id": max_id,
			"errors": errors[:10],
			"message": message,
		}
	except Exception as exc:
		settings.db_set(
			{
				"last_sync_on": now_datetime(),
				"last_sync_status": "Failed",
				"last_sync_message": str(exc)[:140],
			},
			update_modified=True,
		)
		frappe.db.commit()
		frappe.log_error(title="Easy TimePro Sync Failed", message=frappe.get_traceback())
		raise


def create_employee_checkin(punch_doc) -> str | None:
	if not frappe.db.exists("DocType", "Employee Checkin"):
		return None

	exists = frappe.db.exists(
		"Employee Checkin",
		{
			"employee": punch_doc.employee,
			"time": punch_doc.punch_time,
			"log_type": punch_doc.log_type,
		},
	)
	if exists:
		return exists

	checkin = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": punch_doc.employee,
			"time": punch_doc.punch_time,
			"log_type": punch_doc.log_type,
			"device_id": punch_doc.terminal_sn or "Easy TimePro",
			"skip_auto_attendance": 0,
		}
	)
	checkin.insert(ignore_permissions=True)
	return checkin.name


def backfill_unknown_punch_checkins() -> dict:
	"""Fix punch_state 255 / Unknown rows and create missing Employee Checkins."""
	fixed = 0
	checkins = 0
	rows = frappe.get_all(
		"Easy TimePro Punch Log",
		filters=[
			["employee", "is", "set"],
			["employee_checkin", "in", ["", None]],
		],
		fields=["name", "employee", "punch_state", "punch_time", "log_type", "terminal_sn"],
		order_by="punch_time asc",
	)
	for row in rows:
		log_type = resolve_log_type(row.punch_state, row.employee)
		if log_type not in ("IN", "OUT"):
			continue
		if row.log_type != log_type:
			frappe.db.set_value(
				"Easy TimePro Punch Log",
				row.name,
				"log_type",
				log_type,
				update_modified=False,
			)
			fixed += 1
			row.log_type = log_type

		doc = frappe._dict(row)
		try:
			checkin_name = create_employee_checkin(doc)
			if checkin_name:
				frappe.db.set_value(
					"Easy TimePro Punch Log",
					row.name,
					"employee_checkin",
					checkin_name,
					update_modified=False,
				)
				checkins += 1
		except Exception:
			frappe.log_error(
				title=f"Easy TimePro backfill checkin failed: {row.name}",
				message=frappe.get_traceback(),
			)

	frappe.db.commit()
	return {"log_types_fixed": fixed, "employee_checkins_created": checkins}

REALTIME_JOB_ID = "easytimepro_realtime_sync"
LOOP_CACHE_KEY = "easytimepro:sync_loop_alive"


def get_sync_interval_seconds() -> int:
	seconds = int(frappe.db.get_single_value("Easy TimePro Settings", "sync_interval_seconds") or 5)
	return max(5, min(seconds, 3600))


def _mark_loop_alive(seconds: int | None = None):
	ttl = (seconds or get_sync_interval_seconds()) + 60
	frappe.cache.set_value(LOOP_CACHE_KEY, 1, expires_in_sec=ttl)


def _is_loop_alive() -> bool:
	return bool(frappe.cache.get_value(LOOP_CACHE_KEY))


def realtime_sync_tick():
	"""
	Sync once, wait Sync Interval (Seconds), then enqueue the next tick.

	Uses sleep + immediate enqueue (not RQ enqueue_in) so it works without rq-scheduler.
	"""
	import time

	interval = get_sync_interval_seconds()
	_mark_loop_alive(interval)

	try:
		if not frappe.db.get_single_value("Easy TimePro Settings", "enabled"):
			frappe.cache.delete_value(LOOP_CACHE_KEY)
			return
		sync_transactions(force=False)
	except Exception:
		frappe.log_error(title="Easy TimePro realtime sync tick failed", message=frappe.get_traceback())
	finally:
		try:
			if not frappe.db.get_single_value("Easy TimePro Settings", "enabled"):
				frappe.cache.delete_value(LOOP_CACHE_KEY)
				return

			interval = get_sync_interval_seconds()
			_mark_loop_alive(interval)
			time.sleep(interval)
			_mark_loop_alive(interval)
			frappe.enqueue(
				"easytimepro.easy_timepro.sync.realtime_sync_tick",
				queue="default",
				timeout=max(180, interval + 90),
				job_id=f"{REALTIME_JOB_ID}:{frappe.generate_hash(length=10)}",
			)
		except Exception:
			frappe.cache.delete_value(LOOP_CACHE_KEY)
			frappe.log_error(title="Easy TimePro re-queue failed", message=frappe.get_traceback())


def ensure_realtime_loop(force: bool = False):
	"""Start the near-real-time sync loop if it is not already alive."""
	settings = frappe.get_single("Easy TimePro Settings")
	if not settings.enabled:
		frappe.cache.delete_value(LOOP_CACHE_KEY)
		return

	# force: allow restart only if the alive marker expired/missing
	if force:
		# Do not spawn a second chain while one is running
		if _is_loop_alive():
			_mark_loop_alive()
			return

	if _is_loop_alive():
		return

	_mark_loop_alive()
	frappe.enqueue(
		"easytimepro.easy_timepro.sync.realtime_sync_tick",
		queue="default",
		timeout=max(180, get_sync_interval_seconds() + 90),
		job_id=f"{REALTIME_JOB_ID}:{frappe.generate_hash(length=10)}",
	)


def scheduled_sync():
	"""Minute watchdog: restart the seconds-based loop if it stopped."""
	ensure_realtime_loop(force=False)
