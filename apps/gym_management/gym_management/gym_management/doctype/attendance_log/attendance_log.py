# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowtime, today


class AttendanceLog(Document):
	def validate(self):
		if not self.attendance_date:
			self.attendance_date = today()

		self.clear_autofilled_checkout()
		self.validate_duplicate_attendance()
		self.validate_checkout()

	def clear_autofilled_checkout(self):
		"""Frappe _set_defaults copies current time into every empty Time field on insert."""
		if not self.check_in_time or not self.check_out_time or self.flags.get("explicit_check_out"):
			return

		check_in_secs = _time_to_seconds(self.check_in_time)
		check_out_secs = _time_to_seconds(self.check_out_time)
		if check_in_secs is not None and check_out_secs is not None and abs(check_in_secs - check_out_secs) <= 2:
			self.check_out_time = None

	def validate_duplicate_attendance(self):
		if frappe.flags.in_import:
			return

		existing = frappe.db.exists(
			"Attendance Log",
			{
				"gym_member": self.gym_member,
				"attendance_date": self.attendance_date,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(
				_("Attendance for {0} on {1} already exists: {2}").format(
					self.gym_member, self.attendance_date, existing
				)
			)

	def validate_checkout(self):
		if self.check_out_time and not self.check_in_time:
			settings = frappe.get_cached_doc("Gym Settings", "Gym Settings")
			if not settings.allow_checkout_without_checkin:
				frappe.throw(_("Check-in time is required before check-out."))


def _time_to_seconds(value):
	if value in (None, ""):
		return None
	if hasattr(value, "total_seconds"):
		return int(value.total_seconds())
	parts = str(value).split(":")
	try:
		return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]) if len(parts) > 2 else 0)
	except (TypeError, ValueError):
		return None


def _prepare_check_in_doc(doc):
	"""Prevent Frappe from auto-filling check_out_time during insert/save."""
	doc.check_out_time = None
	if "check_out_time" not in doc.dont_update_if_missing:
		doc.dont_update_if_missing.append("check_out_time")


def _set_coords(doc, latitude=None, longitude=None, checkout=False):
	if latitude in (None, "") and longitude in (None, ""):
		return
	try:
		lat = float(latitude) if latitude not in (None, "") else None
		lng = float(longitude) if longitude not in (None, "") else None
	except (TypeError, ValueError):
		frappe.throw(_("Invalid latitude or longitude."))
	if lat is not None and not -90 <= lat <= 90:
		frappe.throw(_("Latitude must be between -90 and 90."))
	if lng is not None and not -180 <= lng <= 180:
		frappe.throw(_("Longitude must be between -180 and 180."))
	if checkout:
		if lat is not None:
			doc.checkout_latitude = lat
		if lng is not None:
			doc.checkout_longitude = lng
	else:
		if lat is not None:
			doc.check_in_latitude = lat
		if lng is not None:
			doc.check_in_longitude = lng


def create_check_in(gym_member: str, latitude=None, longitude=None):
	"""Create or update today's attendance with check-in."""
	attendance_date = today()
	existing = frappe.db.get_value(
		"Attendance Log",
		{"gym_member": gym_member, "attendance_date": attendance_date},
		"name",
	)

	if existing:
		doc = frappe.get_doc("Attendance Log", existing)
		if doc.check_in_time:
			frappe.throw(_("Member already checked in today."))
		doc.check_in_time = nowtime()
		doc.status = "Present"
		_prepare_check_in_doc(doc)
		_set_coords(doc, latitude, longitude)
		doc.save()
		return {"name": doc.name, "message": _("Check-in updated.")}

	doc = frappe.get_doc(
		{
			"doctype": "Attendance Log",
			"gym_member": gym_member,
			"attendance_date": attendance_date,
			"check_in_time": nowtime(),
			"status": "Present",
		}
	)
	_prepare_check_in_doc(doc)
	_set_coords(doc, latitude, longitude)
	doc.insert()
	return {"name": doc.name, "message": _("Checked in successfully.")}


@frappe.whitelist()
def check_out(attendance_log: str, latitude=None, longitude=None):
	doc = frappe.get_doc("Attendance Log", attendance_log)
	if doc.check_out_time:
		frappe.throw(_("Already checked out."))
	doc.flags.explicit_check_out = True
	doc.check_out_time = nowtime()
	_set_coords(doc, latitude, longitude, checkout=True)
	doc.save()
	return {"name": doc.name, "message": _("Checked out successfully.")}
