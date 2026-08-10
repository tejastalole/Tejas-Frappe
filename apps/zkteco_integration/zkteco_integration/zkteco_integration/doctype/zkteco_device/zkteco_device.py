# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class ZKTecoDevice(Document):
	@frappe.whitelist()
	def test_connection(self):
		"""Desk button: connect via pyzk when site is on same LAN as device."""
		from zkteco_integration.utils.device_client import test_device_connection

		frappe.only_for(("System Manager", "HR Manager"))
		return test_device_connection(self.name)

	@frappe.whitelist()
	def sync_now(self, full_sync: int = 0):
		"""Desk button: pull attendance via pyzk (LAN only). Prefer local agent in production."""
		from zkteco_integration.utils.sync import sync_device

		frappe.only_for(("System Manager", "HR Manager"))
		return sync_device(self.name, full_sync=bool(int(full_sync or 0)))

	@frappe.whitelist()
	def clear_error(self):
		frappe.only_for(("System Manager", "HR Manager"))
		self.db_set("last_error", None)
		if self.status == "Error":
			self.db_set("status", "Offline")
		return {"status": "ok"}
