# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Central attendance state machine for biometric event processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Literal

import frappe
from frappe.utils import get_datetime, getdate, time_diff_in_seconds

EventCategory = Literal["Check In Out", "Lunch Break", "Tea Break"]
AttendanceState = Literal["NOT_STARTED", "WORKING", "LUNCH_BREAK", "TEA_BREAK", "COMPLETED", "INCOMPLETE"]

EVENT_DOCTYPES: dict[EventCategory, str] = {
	"Check In Out": "Biometric Check In Check Out",
	"Lunch Break": "Biometric Lunch Break",
	"Tea Break": "Biometric Tea Break",
}

CHECK_IN_OUT_LOG_TYPES = {"Check In", "Check Out"}
BREAK_LOG_TYPES = {"Break Start", "Break End"}


class AttendanceValidationError(frappe.ValidationError):
	pass


class DuplicatePunchError(AttendanceValidationError):
	pass


@dataclass
class DayEvent:
	name: str
	log_type: str
	time: datetime
	source: str = "ADMS"
	is_regularized: bool = False


@dataclass
class AttendanceDayContext:
	employee: str
	attendance_date: date
	check_in_out: list[DayEvent] = field(default_factory=list)
	lunch: list[DayEvent] = field(default_factory=list)
	tea: list[DayEvent] = field(default_factory=list)

	@property
	def check_in(self) -> DayEvent | None:
		for event in self.check_in_out:
			if event.log_type == "Check In":
				return event
		return None

	@property
	def check_out(self) -> DayEvent | None:
		for event in reversed(self.check_in_out):
			if event.log_type == "Check Out":
				return event
		return None

	@property
	def lunch_start(self) -> DayEvent | None:
		for event in self.lunch:
			if event.log_type == "Break Start":
				return event
		return None

	@property
	def lunch_end(self) -> DayEvent | None:
		for event in reversed(self.lunch):
			if event.log_type == "Break End":
				return event
		return None

	@property
	def tea_start(self) -> DayEvent | None:
		for event in self.tea:
			if event.log_type == "Break Start":
				return event
		return None

	@property
	def tea_end(self) -> DayEvent | None:
		for event in reversed(self.tea):
			if event.log_type == "Break End":
				return event
		return None

	@property
	def lunch_used(self) -> bool:
		return bool(self.lunch_start and self.lunch_end)

	@property
	def tea_used(self) -> bool:
		return bool(self.tea_start and self.tea_end)

	@property
	def active_lunch_start(self) -> DayEvent | None:
		return _active_break_start(self.lunch)

	@property
	def active_tea_start(self) -> DayEvent | None:
		return _active_break_start(self.tea)

	def current_state(self) -> AttendanceState:
		if self.check_out:
			return "COMPLETED"
		if self.active_lunch_start:
			return "LUNCH_BREAK"
		if self.active_tea_start:
			return "TEA_BREAK"
		if self.check_in:
			if self._has_incomplete_break():
				return "INCOMPLETE"
			return "WORKING"
		return "NOT_STARTED"

	def _has_incomplete_break(self) -> bool:
		lunch_started = bool(self.lunch_start)
		lunch_ended = bool(self.lunch_end)
		tea_started = bool(self.tea_start)
		tea_ended = bool(self.tea_end)
		return (lunch_started and not lunch_ended) or (tea_started and not tea_ended)


def get_office_policy() -> dict[str, Any]:
	settings = frappe.get_single("Biometric Settings")
	return {
		"office_start_time": settings.office_start_time or "09:00:00",
		"office_end_time": settings.office_end_time or "18:00:00",
		"lunch_break_duration_minutes": int(settings.lunch_break_duration_minutes or 45),
		"lunch_window_start": settings.lunch_window_start or "12:00:00",
		"lunch_window_end": settings.lunch_window_end or "15:00:00",
		"tea_break_duration_minutes": int(settings.tea_break_duration_minutes or 15),
		"tea_window_start": settings.tea_window_start or "16:00:00",
		"tea_window_end": settings.tea_window_end or "18:00:00",
		"duplicate_punch_tolerance_seconds": int(settings.duplicate_punch_tolerance_seconds or 120),
		"allow_checkout_with_incomplete_break": bool(settings.allow_checkout_with_incomplete_break),
		"enable_debug_logging": bool(settings.enable_debug_logging),
	}


def load_day_context(employee: str, punch_time: datetime | str) -> AttendanceDayContext:
	attendance_date = getdate(punch_time)
	day_start = f"{attendance_date} 00:00:00"
	day_end = f"{attendance_date} 23:59:59"
	filters = {"employee": employee, "time": ("between", [day_start, day_end])}

	ctx = AttendanceDayContext(employee=employee, attendance_date=attendance_date)
	for doctype, target in (
		("Biometric Check In Check Out", "check_in_out"),
		("Biometric Lunch Break", "lunch"),
		("Biometric Tea Break", "tea"),
	):
		rows = frappe.get_all(
			doctype,
			filters=filters,
			fields=["name", "log_type", "time", "source", "is_regularized"],
			order_by="time asc, creation asc",
		)
		events = [
			DayEvent(
				name=row.name,
				log_type=row.log_type,
				time=get_datetime(row.time),
				source=row.source or "ADMS",
				is_regularized=bool(row.is_regularized),
			)
			for row in rows
		]
		setattr(ctx, target, events)
	return ctx


def resolve_event_type(
	employee: str,
	punch_status: str | None,
	punch_time: datetime | str,
	ctx: AttendanceDayContext | None = None,
) -> tuple[EventCategory, str]:
	ctx = ctx or load_day_context(employee, punch_time)
	mapped = _lookup_status_mapping(punch_status)
	if mapped:
		return mapped

	if punch_status not in (None, ""):
		hint = _status_hint_to_log_type(punch_status)
		if hint:
			category, log_type = hint
			return category, log_type

	state = ctx.current_state()
	if state == "NOT_STARTED":
		return "Check In Out", "Check In"
	if state == "LUNCH_BREAK":
		return "Lunch Break", "Break End"
	if state == "TEA_BREAK":
		return "Tea Break", "Break End"

	frappe.throw(
		"Unable to determine punch type. Configure punch status mapping on the biometric device "
		"and in Biometric Settings.",
		exc=AttendanceValidationError,
	)


def validate_punch(
	ctx: AttendanceDayContext,
	category: EventCategory,
	log_type: str,
	punch_time: datetime | str | None = None,
	skip_time_window: bool = False,
) -> None:
	state = ctx.current_state()
	policy = get_office_policy()
	punch_time = get_datetime(punch_time) if punch_time else None

	if category == "Check In Out" and log_type == "Check In":
		if ctx.check_in:
			frappe.throw(
				"Employee has already checked in for today.",
				exc=AttendanceValidationError,
			)
		if state == "COMPLETED":
			frappe.throw(
				"No further attendance punches are allowed after check out for today.",
				exc=AttendanceValidationError,
			)
		return

	if category == "Check In Out" and log_type == "Check Out":
		if not ctx.check_in:
			frappe.throw(
				"Regular Check Out is not allowed without Regular Check In.",
				exc=AttendanceValidationError,
			)
		if ctx.check_out:
			frappe.throw(
				"Employee has already checked out for today.",
				exc=AttendanceValidationError,
			)
		if state == "COMPLETED":
			frappe.throw(
				"No further attendance punches are allowed after check out for today.",
				exc=AttendanceValidationError,
			)
		if state == "LUNCH_BREAK":
			frappe.throw(
				"Regular Check Out is not allowed while Lunch Break is active.",
				exc=AttendanceValidationError,
			)
		if state == "TEA_BREAK":
			frappe.throw(
				"Regular Check Out is not allowed while Tea Break is active.",
				exc=AttendanceValidationError,
			)
		if ctx.active_lunch_start and not policy["allow_checkout_with_incomplete_break"]:
			frappe.throw(
				"Lunch Break End is missing. Regular Check Out is blocked until lunch is completed.",
				exc=AttendanceValidationError,
			)
		if ctx.active_tea_start and not policy["allow_checkout_with_incomplete_break"]:
			frappe.throw(
				"Tea Break End is missing. Regular Check Out is blocked until tea break is completed.",
				exc=AttendanceValidationError,
			)
		return

	if category == "Lunch Break" and log_type == "Break Start":
		if not ctx.check_in:
			frappe.throw(
				"Lunch Break Start is not allowed without Regular Check In.",
				exc=AttendanceValidationError,
			)
		if state != "WORKING":
			if state == "LUNCH_BREAK":
				frappe.throw("Lunch Break Start is not allowed while Lunch Break is already active.", exc=AttendanceValidationError)
			if state == "TEA_BREAK":
				frappe.throw("Lunch Break Start is not allowed while Tea Break is active.", exc=AttendanceValidationError)
			if state == "COMPLETED":
				frappe.throw("No further attendance punches are allowed after check out for today.", exc=AttendanceValidationError)
			frappe.throw("Lunch Break Start is allowed only when employee is WORKING.", exc=AttendanceValidationError)
		if ctx.lunch_start:
			frappe.throw("Only one Lunch Break is allowed per working day.", exc=AttendanceValidationError)
		if punch_time and not skip_time_window:
			validate_break_time_window("Lunch Break", log_type, punch_time, ctx.attendance_date, policy)
		return

	if category == "Lunch Break" and log_type == "Break End":
		if not ctx.active_lunch_start:
			frappe.throw(
				"Lunch Break End is not allowed without Lunch Break Start.",
				exc=AttendanceValidationError,
			)
		if ctx.lunch_end:
			frappe.throw("Lunch Break End has already been recorded for today.", exc=AttendanceValidationError)
		if punch_time and not skip_time_window:
			validate_break_time_window("Lunch Break", log_type, punch_time, ctx.attendance_date, policy)
		return

	if category == "Tea Break" and log_type == "Break Start":
		if not ctx.check_in:
			frappe.throw(
				"Tea Break Start is not allowed without Regular Check In.",
				exc=AttendanceValidationError,
			)
		if state != "WORKING":
			if state == "TEA_BREAK":
				frappe.throw("Tea Break Start is not allowed while Tea Break is already active.", exc=AttendanceValidationError)
			if state == "LUNCH_BREAK":
				frappe.throw("Tea Break Start is not allowed while Lunch Break is active.", exc=AttendanceValidationError)
			if state == "COMPLETED":
				frappe.throw("No further attendance punches are allowed after check out for today.", exc=AttendanceValidationError)
			frappe.throw("Tea Break Start is allowed only when employee is WORKING.", exc=AttendanceValidationError)
		if ctx.tea_start:
			frappe.throw("Only one Tea Break is allowed per working day.", exc=AttendanceValidationError)
		if punch_time and not skip_time_window:
			validate_break_time_window("Tea Break", log_type, punch_time, ctx.attendance_date, policy)
		return

	if category == "Tea Break" and log_type == "Break End":
		if not ctx.active_tea_start:
			frappe.throw(
				"Tea Break End is not allowed without Tea Break Start.",
				exc=AttendanceValidationError,
			)
		if ctx.tea_end:
			frappe.throw("Tea Break End has already been recorded for today.", exc=AttendanceValidationError)
		if punch_time and not skip_time_window:
			validate_break_time_window("Tea Break", log_type, punch_time, ctx.attendance_date, policy)
		return

	frappe.throw("Unsupported attendance punch type.", exc=AttendanceValidationError)


def validate_break_time_window(
	category: EventCategory,
	log_type: str,
	punch_time: datetime | str,
	attendance_date: date,
	policy: dict[str, Any] | None = None,
) -> None:
	policy = policy or get_office_policy()
	punch_time = get_datetime(punch_time)

	if category == "Lunch Break":
		window_start = policy["lunch_window_start"]
		window_end = policy["lunch_window_end"]
		label = "Lunch"
	elif category == "Tea Break":
		window_start = policy["tea_window_start"]
		window_end = policy["tea_window_end"]
		label = "Tea"
	else:
		return

	start_dt = _combine_date_time(attendance_date, window_start)
	end_dt = _combine_date_time(attendance_date, window_end)

	if punch_time < start_dt or punch_time > end_dt:
		frappe.throw(
			(
				f"{label} Break {log_type} is only allowed between "
				f"{_format_time(window_start)} and {_format_time(window_end)}."
			),
			exc=AttendanceValidationError,
			title=f"{label} Break Outside Allowed Window",
		)


def _combine_date_time(attendance_date: date, time_value) -> datetime:
	if isinstance(time_value, str):
		time_part = time_value
	else:
		time_part = time_value.strftime("%H:%M:%S")
	return get_datetime(f"{attendance_date} {time_part}")


def _format_time(time_value) -> str:
	if isinstance(time_value, str):
		parts = time_value.split(":")
		hour = int(parts[0])
		minute = parts[1] if len(parts) > 1 else "00"
		period = "AM" if hour < 12 else "PM"
		display_hour = hour % 12 or 12
		return f"{display_hour}:{minute} {period}"
	return str(time_value)


def is_duplicate_punch(
	ctx: AttendanceDayContext,
	category: EventCategory,
	log_type: str,
	punch_time: datetime | str,
	tolerance_seconds: int | None = None,
) -> bool:
	punch_time = get_datetime(punch_time)
	policy = get_office_policy()
	tolerance = tolerance_seconds if tolerance_seconds is not None else policy["duplicate_punch_tolerance_seconds"]

	events = _events_for_category(ctx, category)
	for event in events:
		if event.log_type != log_type:
			continue
		delta = abs(time_diff_in_seconds(event.time, punch_time))
		if delta <= tolerance:
			return True
	return False


def log_debug(message: str, data: dict[str, Any] | None = None) -> None:
	policy = get_office_policy()
	if not policy["enable_debug_logging"]:
		return
	frappe.logger("biometric_attendance").info(f"{message} | {data or {}}")


def get_event_link_field(category: EventCategory) -> str:
	return {
		"Check In Out": "check_in_out",
		"Lunch Break": "lunch_break",
		"Tea Break": "tea_break",
	}[category]


def _events_for_category(ctx: AttendanceDayContext, category: EventCategory) -> list[DayEvent]:
	if category == "Check In Out":
		return ctx.check_in_out
	if category == "Lunch Break":
		return ctx.lunch
	return ctx.tea


def _active_break_start(events: list[DayEvent]) -> DayEvent | None:
	active: DayEvent | None = None
	for event in events:
		if event.log_type == "Break Start":
			active = event
		elif event.log_type == "Break End":
			active = None
	return active


def _lookup_status_mapping(punch_status: str | None) -> tuple[EventCategory, str] | None:
	if punch_status is None:
		return None
	status = str(punch_status).strip()
	if not status:
		return None

	settings = frappe.get_single("Biometric Settings")
	for row in settings.get("punch_status_mappings") or []:
		if str(row.punch_status or "").strip() == status:
			category = row.event_category
			log_type = row.log_type
			if category == "Check In Out" and log_type in CHECK_IN_OUT_LOG_TYPES:
				return category, log_type
			if category in {"Lunch Break", "Tea Break"} and log_type in BREAK_LOG_TYPES:
				return category, log_type
	return None


def _status_hint_to_log_type(status: str) -> tuple[EventCategory, str] | None:
	value = str(status).strip().upper()
	if value in {"0", "I", "IN", "CHECKIN", "C/IN"}:
		return "Check In Out", "Check In"
	if value in {"1", "O", "OUT", "CHECKOUT", "C/OUT"}:
		return "Check In Out", "Check Out"
	if value in {"2", "LUNCH IN", "LUNCH START", "L/IN"}:
		return "Lunch Break", "Break Start"
	if value in {"3", "LUNCH OUT", "LUNCH END", "L/OUT"}:
		return "Lunch Break", "Break End"
	if value in {"4", "TEA IN", "TEA START", "T/IN"}:
		return "Tea Break", "Break Start"
	if value in {"5", "TEA OUT", "TEA END", "T/OUT"}:
		return "Tea Break", "Break End"
	return None
