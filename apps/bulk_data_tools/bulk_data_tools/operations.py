# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Core bulk operations for DocType records."""

from __future__ import annotations

import csv
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

# Never allow bulk delete of these (system integrity)
SYSTEM_PROTECTED = {
	"DocType",
	"DocField",
	"DocPerm",
	"DocType Link",
	"DocType Action",
	"DocType State",
	"Module Def",
	"User",
	"Role",
	"Has Role",
	"Custom Field",
	"Property Setter",
	"Client Script",
	"Server Script",
	"Workspace",
	"Page",
	"Report",
	"File",
	"Error Log",
	"Activity Log",
	"Version",
	"Comment",
	"Communication",
	"Scheduled Job Type",
	"Scheduler Event",
	"Installed Application",
	"Patch Log",
	"Session Default",
	"DefaultValue",
	"Singles",
	"Bulk Data Tool",
	"Bulk Data Operation Log",
	"Bulk Protected DocType",
	"Company",
	"Currency",
	"Country",
	"Language",
}


def get_protected_doctypes() -> set[str]:
	protected = set(SYSTEM_PROTECTED)
	try:
		tool = frappe.get_single("Bulk Data Tool")
		for row in tool.get("extra_protected_doctypes") or []:
			if row.doctype_name:
				protected.add(row.doctype_name)
	except Exception:
		pass
	return protected


def assert_can_modify(doctype: str) -> None:
	if not doctype:
		frappe.throw(_("Please select a DocType."))

	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("DocType {0} does not exist.").format(doctype))

	meta = frappe.get_meta(doctype)
	if meta.issingle:
		frappe.throw(_("Cannot bulk-delete Single DocType {0}.").format(doctype))
	if meta.istable:
		frappe.throw(_("Cannot bulk-delete Child Table {0} directly.").format(doctype))
	if doctype in get_protected_doctypes():
		frappe.throw(
			_("DocType {0} is protected and cannot be bulk-deleted.").format(doctype)
		)


def parse_filters(filters_json: str | None, docstatus_filter: str = "All") -> list:
	filters: list = []
	raw = (filters_json or "").strip()
	if raw:
		try:
			parsed = json.loads(raw)
		except json.JSONDecodeError as exc:
			frappe.throw(_("Invalid Filters JSON: {0}").format(str(exc)))
		if not isinstance(parsed, list):
			frappe.throw(_("Filters JSON must be a list, e.g. [[\"field\",\"=\",\"value\"]]"))
		filters.extend(parsed)

	if docstatus_filter and docstatus_filter != "All":
		mapping = {
			"Draft (0)": 0,
			"Submitted (1)": 1,
			"Cancelled (2)": 2,
		}
		if docstatus_filter in mapping:
			filters.append(["docstatus", "=", mapping[docstatus_filter]])

	return filters


def count_records(doctype: str, filters: list | None = None) -> int:
	assert_can_modify(doctype)
	return frappe.db.count(doctype, filters=filters or None)


def preview_records(doctype: str, filters: list | None = None, limit: int = 20) -> list[dict]:
	assert_can_modify(doctype)
	names = frappe.get_all(
		doctype,
		filters=filters or None,
		fields=["name", "modified", "owner"],
		limit_page_length=limit,
		order_by="modified desc",
	)
	return names


def export_names(doctype: str, filters: list | None = None) -> str:
	"""Write matching names to a private file and return file URL."""
	assert_can_modify(doctype)
	rows = frappe.get_all(
		doctype,
		filters=filters or None,
		fields=["name", "creation", "modified", "owner", "docstatus"],
		limit_page_length=0,
		order_by="creation asc",
	)

	fname = f"bulk_export_{doctype}_{frappe.generate_hash(length=8)}.csv".replace(" ", "_")
	fpath = frappe.get_site_path("private", "files", fname)
	with open(fpath, "w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(
			handle, fieldnames=["name", "creation", "modified", "owner", "docstatus"]
		)
		writer.writeheader()
		for row in rows:
			writer.writerow(row)

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"file_url": f"/private/files/{fname}",
			"is_private": 1,
			"attached_to_doctype": "Bulk Data Tool",
			"attached_to_name": "Bulk Data Tool",
		}
	).insert(ignore_permissions=True)

	return file_doc.file_url


def delete_records(
	doctype: str,
	filters: list | None = None,
	batch_size: int = 100,
	force: bool = False,
	delete_permanently: bool = False,
	dry_run: bool = True,
) -> dict[str, Any]:
	assert_can_modify(doctype)
	batch_size = max(1, min(cint(batch_size) or 100, 500))
	matched = frappe.db.count(doctype, filters=filters or None)

	result = {
		"ok": True,
		"count": matched,
		"deleted": 0,
		"errors": 0,
		"dry_run": dry_run,
		"sample_errors": [],
	}

	if dry_run:
		result["message"] = _("Dry run: {0} record(s) would be deleted.").format(matched)
		return result

	deleted = 0
	errors = 0
	sample_errors: list[str] = []

	while True:
		names = frappe.get_all(
			doctype,
			filters=filters or None,
			pluck="name",
			limit_page_length=batch_size,
			order_by="creation asc",
		)
		if not names:
			break

		for name in names:
			try:
				frappe.delete_doc(
					doctype,
					name,
					ignore_permissions=True,
					force=force,
					delete_permanently=delete_permanently,
				)
				deleted += 1
			except Exception:
				errors += 1
				if len(sample_errors) < 10:
					sample_errors.append(f"{name}: {frappe.get_traceback().splitlines()[-1]}")
		frappe.db.commit()

	result["deleted"] = deleted
	result["errors"] = errors
	result["sample_errors"] = sample_errors
	result["count"] = frappe.db.count(doctype, filters=filters or None)
	if errors and deleted:
		result["message"] = _("Deleted {0}, errors {1}. Remaining {2}.").format(
			deleted, errors, result["count"]
		)
	elif errors and not deleted:
		result["ok"] = False
		result["message"] = _("No records deleted. Errors: {0}.").format(errors)
	else:
		result["message"] = _("Deleted {0} record(s). Remaining {1}.").format(
			deleted, result["count"]
		)
	return result


def clear_recycle_bin(doctype: str, dry_run: bool = True) -> dict[str, Any]:
	assert_can_modify(doctype)
	# Deleted documents live in tabDeleted Document
	filters = {"deleted_doctype": doctype}
	matched = frappe.db.count("Deleted Document", filters)

	if dry_run:
		return {
			"ok": True,
			"count": matched,
			"deleted": 0,
			"dry_run": True,
			"message": _("Dry run: {0} Recycle Bin item(s) would be cleared.").format(matched),
		}

	frappe.db.delete("Deleted Document", filters)
	frappe.db.commit()
	return {
		"ok": True,
		"count": 0,
		"deleted": matched,
		"dry_run": False,
		"message": _("Cleared {0} Recycle Bin item(s) for {1}.").format(matched, doctype),
	}


def start_log(action: str, doctype: str, filters: list, dry_run: bool) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Bulk Data Operation Log",
			"action": action,
			"target_doctype": doctype,
			"status": "Running",
			"started_at": now_datetime(),
			"requested_by": frappe.session.user,
			"dry_run": 1 if dry_run else 0,
			"filters_used": json.dumps(filters or [], indent=2),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def finish_log(
	log_name: str,
	status: str,
	matched: int = 0,
	deleted: int = 0,
	errors: int = 0,
	details: str | None = None,
	error_details: str | None = None,
) -> None:
	frappe.db.set_value(
		"Bulk Data Operation Log",
		log_name,
		{
			"status": status,
			"ended_at": now_datetime(),
			"matched_count": matched,
			"deleted_count": deleted,
			"error_count": errors,
			"details": details,
			"error_details": error_details,
		},
		update_modified=True,
	)
	frappe.db.commit()
