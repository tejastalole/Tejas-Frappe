# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	"""Rename latitude/longitude to check_in_latitude/check_in_longitude."""
	if frappe.db.has_column("Attendance Log", "latitude"):
		rename_field("Attendance Log", "latitude", "check_in_latitude")

	if frappe.db.has_column("Attendance Log", "longitude"):
		rename_field("Attendance Log", "longitude", "check_in_longitude")
