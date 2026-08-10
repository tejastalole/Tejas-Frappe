# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Scheduled TCP pull."""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime


def pull_attendance():
	settings = frappe.get_single("Biometric Settings")
	if not settings.enabled or not settings.enable_tcp_pull:
		return

	interval = settings.pull_every or 10
	if settings.last_pull_at:
		next_allowed = add_to_date(get_datetime(settings.last_pull_at), minutes=interval)
		if now_datetime() < next_allowed:
			return

	from biometric_integration.zk_pull import pull_all_enabled

	pull_all_enabled()
