# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe import _
from frappe.utils import get_url, today


def has_app_permission():
	"""Show Gym app on Frappe apps screen."""
	if frappe.session.user == "Guest":
		return False
	return bool(set(frappe.get_roles()) & {"System Manager", "Gym Manager", "Gym User", "Administrator"})


def _ensure_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to use the Gym app."), frappe.AuthenticationError)

	roles = set(frappe.get_roles())
	if not roles & {"System Manager", "Gym Manager", "Gym User", "Administrator"}:
		frappe.throw(_("You do not have permission to use the Gym app."), frappe.PermissionError)


@frappe.whitelist()
def get_app_config():
	"""Boot config for the mobile PWA."""
	_ensure_access()
	settings = frappe.get_cached_doc("Gym Settings", "Gym Settings")
	return {
		"user": frappe.session.user,
		"gym_name": settings.gym_name or "SG Fitness",
		"today": today(),
	}


@frappe.whitelist()
def get_dashboard():
	_ensure_access()
	today_date = today()
	return {
		"active_members": frappe.db.count("Gym Member", {"status": "Active"}),
		"today_attendance": frappe.db.count("Attendance Log", {"attendance_date": today_date}),
		"active_memberships": frappe.db.count("Gym Membership", {"status": "Active"}),
		"expiring_soon": frappe.db.count(
			"Gym Membership",
			{"status": "Active", "end_date": ["between", [today_date, frappe.utils.add_days(today_date, 7)]]},
		),
	}


@frappe.whitelist()
def get_members(search=None, limit=30):
	_ensure_access()
	limit = min(int(limit or 30), 100)
	filters = {"status": "Active"}
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [
			["member_name", "like", like],
			["mobile_no", "like", like],
			["name", "like", like],
		]

	members = frappe.get_all(
		"Gym Member",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"member_name",
			"mobile_no",
			"image",
			"status",
			"assigned_trainer",
			"join_date",
		],
		order_by="member_name asc",
		limit_page_length=limit,
	)

	for member in members:
		if member.get("image"):
			member["image"] = get_url(member["image"])
		today_attendance = frappe.db.get_value(
			"Attendance Log",
			{"gym_member": member.name, "attendance_date": today()},
			["name", "check_in_time", "check_out_time"],
			as_dict=True,
		)
		member["checked_in_today"] = bool(today_attendance and today_attendance.check_in_time)
		if today_attendance:
			member["today_attendance_log"] = today_attendance.name
			member["today_check_in_time"] = today_attendance.check_in_time
			member["today_check_out_time"] = today_attendance.check_out_time
		member["active_membership"] = frappe.db.get_value(
			"Gym Membership",
			{
				"gym_member": member.name,
				"status": "Active",
				"end_date": [">=", today()],
			},
			["membership_plan", "end_date", "start_date"],
			as_dict=True,
		)
		if member.get("active_membership") and member["active_membership"].get("membership_plan"):
			member["plan_name"] = member["active_membership"]["membership_plan"]
		if member.get("assigned_trainer"):
			member["trainer_name"] = member["assigned_trainer"]

	return members


def _get_plan_details(plan_name):
	if not plan_name:
		return None
	return frappe.db.get_value(
		"Membership Plan",
		plan_name,
		["plan_name", "duration_days", "fee", "description", "is_active"],
		as_dict=True,
	)


def _get_trainer_details(trainer_name):
	if not trainer_name:
		return None
	return frappe.db.get_value(
		"Gym Trainer",
		trainer_name,
		["name", "trainer_name", "mobile_no", "email", "specialization", "status", "remarks"],
		as_dict=True,
	)


def _enrich_membership(membership_row):
	if not membership_row:
		return None
	row = dict(membership_row)
	row["plan"] = _get_plan_details(row.get("membership_plan"))
	return row


@frappe.whitelist()
def get_member(gym_member):
	_ensure_access()
	doc = frappe.get_doc("Gym Member", gym_member)

	active_membership = frappe.db.get_value(
		"Gym Membership",
		{
			"gym_member": gym_member,
			"status": "Active",
			"end_date": [">=", today()],
		},
		[
			"name",
			"membership_plan",
			"start_date",
			"end_date",
			"status",
			"amount",
			"payment_reference",
			"remarks",
		],
		as_dict=True,
	)

	memberships = frappe.get_all(
		"Gym Membership",
		filters={"gym_member": gym_member},
		fields=[
			"name",
			"membership_plan",
			"start_date",
			"end_date",
			"status",
			"amount",
			"payment_reference",
		],
		order_by="start_date desc",
		limit=10,
	)

	attendance = frappe.get_all(
		"Attendance Log",
		filters={"gym_member": gym_member},
		fields=[
			"name",
			"attendance_date",
			"check_in_time",
			"check_out_time",
			"check_in_latitude",
			"check_in_longitude",
			"checkout_latitude",
			"checkout_longitude",
		],
		order_by="attendance_date desc",
		limit=10,
	)

	image = get_url(doc.image) if doc.image else None
	trainer = _get_trainer_details(doc.assigned_trainer)

	return {
		"name": doc.name,
		"member_name": doc.member_name,
		"mobile_no": doc.mobile_no,
		"email": doc.email,
		"status": doc.status,
		"join_date": doc.join_date,
		"gender": doc.gender,
		"date_of_birth": doc.date_of_birth,
		"address": doc.address,
		"emergency_contact_name": doc.emergency_contact_name,
		"emergency_contact_phone": doc.emergency_contact_phone,
		"assigned_trainer": doc.assigned_trainer,
		"remarks": doc.remarks,
		"image": image,
		"trainer": trainer,
		"membership": _enrich_membership(active_membership),
		"memberships": [_enrich_membership(m) for m in memberships],
		"attendance": attendance,
		"checked_in_today": bool(
			frappe.db.exists(
				"Attendance Log",
				{
					"gym_member": gym_member,
					"attendance_date": today(),
					"check_in_time": ["is", "set"],
				},
			)
		),
		"today_attendance": frappe.db.get_value(
			"Attendance Log",
			{"gym_member": gym_member, "attendance_date": today()},
			["name", "check_in_time", "check_out_time"],
			as_dict=True,
		),
	}


@frappe.whitelist()
def check_in(gym_member, latitude=None, longitude=None):
	_ensure_access()
	if not frappe.has_permission("Attendance Log", "create"):
		frappe.throw(_("Not permitted to create attendance."), frappe.PermissionError)

	from gym_management.gym_management.doctype.attendance_log.attendance_log import create_check_in

	return create_check_in(gym_member, latitude=latitude, longitude=longitude)


@frappe.whitelist()
def check_out(attendance_log, latitude=None, longitude=None):
	_ensure_access()
	if not frappe.has_permission("Attendance Log", "write"):
		frappe.throw(_("Not permitted to update attendance."), frappe.PermissionError)

	from gym_management.gym_management.doctype.attendance_log.attendance_log import (
		check_out as do_check_out,
	)

	return do_check_out(attendance_log, latitude=latitude, longitude=longitude)


@frappe.whitelist()
def get_today_attendance():
	_ensure_access()
	return frappe.db.sql(
		"""
		SELECT
			a.name,
			a.gym_member,
			m.member_name,
			a.check_in_time,
			a.check_out_time,
			a.status
		FROM `tabAttendance Log` a
		INNER JOIN `tabGym Member` m ON m.name = a.gym_member
		WHERE a.attendance_date = %(today)s
		ORDER BY a.check_in_time DESC
		""",
		{"today": today()},
		as_dict=True,
	)
