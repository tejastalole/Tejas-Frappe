# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document
from frappe.utils import today


class GymMember(Document):
	def validate(self):
		if not self.join_date:
			self.join_date = today()


@frappe.whitelist()
def check_in_member(gym_member: str, latitude=None, longitude=None):
	"""Create today's attendance with check-in time and optional GPS."""
	from gym_management.gym_management.doctype.attendance_log.attendance_log import (
		create_check_in,
	)

	return create_check_in(gym_member, latitude=latitude, longitude=longitude)


@frappe.whitelist()
def get_active_membership(gym_member: str):
	return frappe.db.get_value(
		"Gym Membership",
		{
			"gym_member": gym_member,
			"status": "Active",
			"end_date": [">=", today()],
		},
		["name", "membership_plan", "end_date"],
		as_dict=True,
	)
