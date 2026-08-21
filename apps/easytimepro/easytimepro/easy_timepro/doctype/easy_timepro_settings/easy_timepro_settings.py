# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class EasyTimeProSettings(Document):
	def validate(self):
		seconds = cint(self.sync_interval_seconds)
		if seconds < 5:
			self.sync_interval_seconds = 5
		elif seconds > 3600:
			self.sync_interval_seconds = 3600

	def on_update(self):
		from easytimepro.easy_timepro.sync import ensure_realtime_loop

		# Restart / kick the 5-second style background loop
		ensure_realtime_loop(force=True)


@frappe.whitelist()
def test_connection():
	from easytimepro.easy_timepro.api_client import EasyTimeProClient

	client = EasyTimeProClient.from_settings()
	token = client.get_token(force=True)
	count = client.get_transaction_count()
	return {
		"ok": True,
		"message": f"Connected. Token OK. Transactions available: {count}",
		"count": count,
	}


@frappe.whitelist()
def sync_now():
	from easytimepro.easy_timepro.sync import sync_transactions

	return sync_transactions(force=True)


@frappe.whitelist()
def sync_employee_ids():
	"""Pull Easy TimePro Employee IDs into Employee.attendance_device_id and remap punches."""
	from easytimepro.easy_timepro.sync import (
		remap_punch_log_employees,
		sync_employee_device_ids_from_easytimepro,
	)

	mapped = sync_employee_device_ids_from_easytimepro()
	remapped = remap_punch_log_employees()
	return {**mapped, **remapped}


@frappe.whitelist()
def get_sync_interval_seconds():
	return max(5, cint(frappe.db.get_single_value("Easy TimePro Settings", "sync_interval_seconds") or 5))
