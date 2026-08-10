# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Server-side validation for manual attendance event entry."""

from __future__ import annotations

import frappe

from biometric_integration.attendance_state import (
	EVENT_DOCTYPES,
	EventCategory,
	load_day_context,
	resolve_event_type,
	validate_punch,
)
from biometric_integration.attendance_summary import refresh_attendance_day_summary


CATEGORY_BY_DOCTYPE = {v: k for k, v in EVENT_DOCTYPES.items()}


def validate_event_before_insert(doc) -> None:
	if frappe.flags.in_biometric_event_insert:
		return
	if doc.get("is_regularized"):
		return
	if doc.source not in (None, "", "Manual"):
		return

	category: EventCategory = CATEGORY_BY_DOCTYPE[doc.doctype]
	ctx = load_day_context(doc.employee, doc.time)
	validate_punch(ctx, category, doc.log_type, doc.time)


def after_event_insert(doc) -> None:
	if frappe.flags.in_biometric_event_insert:
		return
	refresh_attendance_day_summary(doc.employee, doc.attendance_date or doc.time)
