# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Whitelisted API for Bulk Data Tools."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from bulk_data_tools.operations import (
	clear_recycle_bin,
	count_records,
	delete_records,
	export_names,
	finish_log,
	parse_filters,
	preview_records,
	start_log,
)


@frappe.whitelist()
def run_action(
	action: str,
	target_doctype: str,
	filters_json: str = "[]",
	docstatus_filter: str = "All",
	batch_size: int = 100,
	force_delete: int = 0,
	delete_permanently: int = 0,
	dry_run: int = 1,
	confirm_text: str = "",
) -> dict[str, Any]:
	frappe.only_for(("System Manager", "Bulk Data Manager"))

	filters = parse_filters(filters_json, docstatus_filter)
	is_dry = bool(cint(dry_run))
	action = (action or "").strip()

	if action == "count_records":
		log = start_log("Count", target_doctype, filters, True)
		try:
			count = count_records(target_doctype, filters)
			finish_log(log, "Success", matched=count, details=json.dumps({"count": count}))
			return {
				"ok": True,
				"count": count,
				"message": _("{0} has {1} matching record(s).").format(target_doctype, count),
			}
		except Exception:
			finish_log(log, "Failed", error_details=frappe.get_traceback())
			raise

	if action == "preview_records":
		log = start_log("Preview", target_doctype, filters, True)
		try:
			rows = preview_records(target_doctype, filters)
			count = count_records(target_doctype, filters)
			finish_log(
				log,
				"Success",
				matched=count,
				details=json.dumps({"sample": rows}, default=str, indent=2),
			)
			return {
				"ok": True,
				"count": count,
				"sample": rows,
				"message": _("Showing {0} of {1} record(s).").format(len(rows), count),
			}
		except Exception:
			finish_log(log, "Failed", error_details=frappe.get_traceback())
			raise

	if action == "export_names":
		log = start_log("Export", target_doctype, filters, True)
		try:
			count = count_records(target_doctype, filters)
			url = export_names(target_doctype, filters)
			finish_log(log, "Success", matched=count, details=url)
			return {
				"ok": True,
				"count": count,
				"download_url": url,
				"message": _("Exported {0} name(s).").format(count),
			}
		except Exception:
			finish_log(log, "Failed", error_details=frappe.get_traceback())
			raise

	if action == "delete_records":
		if not is_dry and (confirm_text or "").strip().upper() != "DELETE":
			frappe.throw(_('Type "DELETE" in Confirm field to run a real delete (or keep Dry Run checked).'))

		log = start_log("Delete", target_doctype, filters, is_dry)
		try:
			result = delete_records(
				target_doctype,
				filters=filters,
				batch_size=cint(batch_size) or 100,
				force=bool(cint(force_delete)),
				delete_permanently=bool(cint(delete_permanently)),
				dry_run=is_dry,
			)
			status = "Success"
			if result.get("errors") and result.get("deleted"):
				status = "Partial"
			elif result.get("ok") is False:
				status = "Failed"
			finish_log(
				log,
				status,
				matched=result.get("count", 0) if is_dry else result.get("deleted", 0) + result.get("count", 0),
				deleted=result.get("deleted", 0),
				errors=result.get("errors", 0),
				details=json.dumps(result, default=str, indent=2),
				error_details="\n".join(result.get("sample_errors") or []) or None,
			)
			return result
		except Exception:
			finish_log(log, "Failed", error_details=frappe.get_traceback())
			raise

	if action == "clear_recycle_bin":
		if not is_dry and (confirm_text or "").strip().upper() != "DELETE":
			frappe.throw(_('Type "DELETE" in Confirm field to clear Recycle Bin (or keep Dry Run checked).'))

		log = start_log("Clear Recycle Bin", target_doctype, filters, is_dry)
		try:
			result = clear_recycle_bin(target_doctype, dry_run=is_dry)
			finish_log(
				log,
				"Success",
				matched=result.get("count", 0) if is_dry else result.get("deleted", 0),
				deleted=result.get("deleted", 0),
				details=json.dumps(result, default=str, indent=2),
			)
			return result
		except Exception:
			finish_log(log, "Failed", error_details=frappe.get_traceback())
			raise

	frappe.throw(_("Unknown action: {0}").format(action))
