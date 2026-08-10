# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Whitelisted desk APIs."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from biometric_integration.zk_pull import pull_all_enabled, pull_device as _pull_device, test_connection


@frappe.whitelist()
def pull_now() -> dict[str, Any]:
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	settings = frappe.get_single("Biometric Settings")
	if not settings.enabled:
		frappe.throw(_("Biometric Integration is disabled in Settings."))
	return pull_all_enabled()


@frappe.whitelist()
def pull_device(device: str) -> dict[str, Any]:
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	return _pull_device(device)


@frappe.whitelist()
def test_device_connection(device: str) -> dict[str, Any]:
	frappe.only_for(("System Manager", "Biometric Manager", "HR Manager"))
	return test_connection(device)
