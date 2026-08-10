# Copyright (c) 2026, Exacuer and contributors
# For license information, please see license.txt

"""Scheduled maintenance tasks (cloud side)."""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, now_datetime


def mark_stale_devices_offline():
	minutes = frappe.db.get_single_value("ZKTeco Settings", "stale_offline_minutes") or 15
	cutoff = add_to_date(now_datetime(), minutes=-int(minutes))
	devices = frappe.get_all(
		"ZKTeco Device",
		filters={"status": "Online", "last_seen": ("<", cutoff)},
		pluck="name",
	)
	for name in devices:
		frappe.db.set_value("ZKTeco Device", name, "status", "Offline", update_modified=False)
	if devices:
		frappe.db.commit()
