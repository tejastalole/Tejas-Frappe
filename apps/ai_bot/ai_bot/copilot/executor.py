# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Execute structured copilot intents against Frappe with permission checks."""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, getdate, nowdate

from ai_bot.copilot.entity_resolver import resolve_record
from ai_bot.services.site_data import (
	format_record_detail,
	format_search_results,
	format_site_overview,
	get_list_fields,
	get_record_summary,
	get_site_overview,
	search_in_doctype,
	search_site_wide,
)
from ai_bot.copilot.security import log_action
from ai_bot.utils.create_sales_order import create_sales_order, resolve_customer
from ai_bot.utils.doctype_discovery import get_recent_records, get_config
from ai_bot.utils.filters import filters_summary


def execute_intents(intents: list[dict], raw_message: str = "") -> dict:
	if not intents:
		return {
			"status": "need_input",
			"message": _("Please enter a request."),
			"data": {},
			"actions": [],
		}

	intents = _sort_intents_for_execution(intents)
	messages = []
	all_actions = []
	worst_status = "success"
	results = []
	resolved_by_hint: dict[str, str] = {}

	for intent in intents:
		hint = (intent.get("filters") or {}).get("_hint")
		if hint and hint in resolved_by_hint:
			intent = dict(intent)
			intent["filters"] = dict(intent.get("filters") or {})
			intent["filters"]["name"] = resolved_by_hint[hint]
			intent["filters"].pop("_hint", None)

		result = execute_intent(intent, raw_message)

		if hint and result.get("data", {}).get("name"):
			resolved_by_hint[hint] = result["data"]["name"]
		results.append(result)
		if result.get("message"):
			messages.append(result["message"])
		all_actions.extend(result.get("actions") or [])
		status = result.get("status", "success")
		if status == "error":
			worst_status = "error"
		elif status in ("warning", "need_input") and worst_status != "error":
			worst_status = status

	if len(messages) == 1:
		body = messages[0]
	else:
		body = "<p>" + _("Completed {0} steps:").format(len(messages)) + "</p><ul>"
		body += "".join(f"<li>{m}</li>" for m in messages)
		body += "</ul>"

	return {
		"status": worst_status,
		"message": body,
		"data": {"results": results},
		"actions": all_actions[:8],
	}


def execute_intent(intent: dict, raw_message: str = "") -> dict:
	action = intent.get("action")

	if action == "compound":
		return execute_intents(intent.get("intents") or [], raw_message)

	if action == "clarification":
		return {
			"status": intent.get("status", "need_input"),
			"message": intent.get("message", _("Please clarify your request.")),
			"data": {},
			"actions": [],
		}

	handlers = {
		"read": _execute_read,
		"create": _execute_create,
		"update": _execute_update,
		"delete": _execute_delete,
		"report": _execute_report,
		"analyze": _execute_analyze,
		"summarize": _execute_summarize,
		"approve": _execute_submit,
		"reject": _execute_reject,
		"cancel": _execute_cancel_doc,
		"email": _execute_email,
		"notify": _execute_notify,
	}

	handler = handlers.get(action)
	if not handler:
		return {
			"status": "error",
			"message": _("Unsupported action: {0}").format(action),
			"data": {},
			"actions": [],
		}

	try:
		return handler(intent, raw_message)
	except frappe.PermissionError:
		return {
			"status": "error",
			"message": _("You do not have permission for this operation."),
			"data": {},
			"actions": [],
		}
	except Exception as exc:
		frappe.log_error(title="AI Bot Copilot")
		return {
			"status": "error",
			"message": str(exc),
			"data": {},
			"actions": [],
		}


def _execute_read(intent: dict, raw_message: str) -> dict:
	read_type = intent.get("read_type")

	if read_type == "site_overview":
		overview = get_site_overview()
		return {
			"status": "success",
			"message": format_site_overview(overview),
			"data": overview,
			"actions": [],
		}

	if read_type == "site_search":
		return _execute_site_search(intent)

	if read_type == "detail":
		return _execute_record_detail(intent)

	doctype = intent.get("doctype")
	if not doctype:
		return {
			"status": "need_input",
			"message": _("Please specify what to read (e.g. customers, sales orders)."),
			"data": {},
			"actions": [],
		}

	if not frappe.has_permission(doctype, "read"):
		return _permission_error()

	filters = _prepare_filters(intent.get("filters") or {}, doctype)
	fields = intent.get("fields") or get_list_fields(doctype)

	if read_type == "aggregate":
		config = get_config(doctype)
		amount_field = config.get("amount_field")
		if not amount_field:
			return {
				"status": "need_input",
				"message": _("{0} does not have a total amount field to sum.").format(doctype),
				"data": {},
				"actions": [],
			}
		rows = frappe.get_all(doctype, filters=filters, fields=[amount_field])
		total = sum(flt(r.get(amount_field)) for r in rows)
		currency = frappe.db.get_default("currency")
		summary = filters_summary(filters, doctype)
		return {
			"status": "success",
			"message": _("Total <b>{0}</b> for {1} ({2} records): <b>{3}</b>").format(
				frappe.unscrub(amount_field),
				doctype,
				len(rows),
				fmt_money(total, currency=currency),
			)
			+ (f" — {summary}" if summary else ""),
			"data": {"total": total, "count": len(rows)},
			"actions": [],
		}

	if read_type == "count":
		count = frappe.db.count(doctype, filters)
		summary = filters_summary(filters, doctype)
		label = summary or _("all")
		return {
			"status": "success",
			"message": _(
				"There are <b>{0}</b> {1} record(s) ({2})."
			).format(count, doctype, label),
			"data": {"count": count, "filters": filters},
			"actions": [],
		}

	# Single record by name — show full detail
	if filters.get("name") and frappe.db.exists(doctype, filters["name"]):
		return _execute_record_detail(
			{
				"doctype": doctype,
				"filters": {"name": filters["name"]},
				"read_type": "detail",
			}
		)

	# Text search within doctype
	search_q = intent.get("search_query") or (intent.get("filters") or {}).get("_hint")
	if search_q:
		records = search_in_doctype(doctype, search_q, limit=10)
		if records:
			from ai_bot.services.site_data import format_record_lines

			lines = format_record_lines(doctype, records)
			return {
				"status": "success",
				"message": _("<p><b>{0}</b> matching <i>{1}</i>:</p><ul>{2}</ul>").format(
					len(records),
					frappe.utils.escape_html(search_q),
					"".join(f"<li>{line}</li>" for line in lines),
				),
				"data": {"records": records},
				"actions": [
					{
						"type": "open",
						"doctype": doctype,
						"name": r["name"],
						"label": r["name"],
					}
					for r in records[:5]
				],
			}

	limit = 10
	records = frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		limit=limit,
		order_by="modified desc",
	)

	if not records:
		return {
			"status": "success",
			"message": _("No {0} records found matching your criteria.").format(doctype),
			"data": {"records": []},
			"actions": [],
		}

	lines = [_format_record_line(doctype, r, fields) for r in records]
	summary = filters_summary(filters, doctype)
	header = _("Found {0} {1}(s)").format(len(records), doctype)
	if summary:
		header += f" ({summary})"
	if len(records) == limit:
		header += _(" — showing latest {0}").format(limit)

	actions = [
		{
			"type": "open",
			"doctype": doctype,
			"name": r["name"],
			"label": r["name"],
		}
		for r in records[:5]
	]

	return {
		"status": "success",
		"message": f"<p>{header}</p><ul>{''.join(f'<li>{line}</li>' for line in lines)}</ul>",
		"data": {"records": records},
		"actions": actions,
	}


def _execute_create(intent: dict, raw_message: str) -> dict:
	doctype = intent["doctype"]
	data = intent.get("data") or {}

	if not frappe.has_permission(doctype, "create"):
		return _permission_error()

	if doctype == "Sales Order" and data.get("customer") and data.get("items"):
		item = data["items"][0]
		so = create_sales_order(
			data["customer"],
			item.get("item_code") or item.get("item_name"),
			item.get("qty", 1),
			item.get("rate"),
		)
		return {
			"status": "success",
			"message": _("Sales Order <b>{0}</b> created successfully.").format(so.name),
			"data": {"name": so.name},
			"actions": [
				{
					"type": "open",
					"doctype": "Sales Order",
					"name": so.name,
					"label": _("Open {0}").format(so.name),
				}
			],
		}

	if doctype == "Customer" and data.get("customer_name"):
		if frappe.db.exists("Customer", {"customer_name": data["customer_name"]}):
			return {
				"status": "warning",
				"message": _("Customer <b>{0}</b> already exists.").format(data["customer_name"]),
				"data": {},
				"actions": [],
			}
		doc = frappe.get_doc({"doctype": "Customer", "customer_name": data["customer_name"]})
		doc.insert()
		return _created_response(doc)

	if doctype == "Employee" and data.get("employee_name"):
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": data["employee_name"].split()[0],
				"employee_name": data["employee_name"],
			}
		)
		doc.insert()
		return _created_response(doc)

	if doctype == "Item" and data.get("item_name"):
		item_code = frappe.scrub(data["item_name"]).replace("-", "_").upper()[:140]
		if frappe.db.exists("Item", item_code):
			item_code = f"{item_code}-{frappe.generate_hash(length=4)}"
		doc = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": data["item_name"],
				"item_group": frappe.db.get_single_value("Stock Settings", "item_group")
				or "Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		)
		doc.insert()
		return _created_response(doc)

	if doctype == "Quotation" and data.get("customer"):
		return _create_quotation(data)

	if not data:
		return {
			"status": "need_input",
			"message": _("Please provide details to create {0}.").format(doctype),
			"data": {},
			"actions": [],
		}

	doc = frappe.get_doc({"doctype": doctype, **data})
	doc.insert()
	return _created_response(doc)


def _create_quotation(data: dict) -> dict:
	customer = resolve_customer(data["customer"])
	if not customer:
		return {
			"status": "error",
			"message": _("Customer <b>{0}</b> not found.").format(data["customer"]),
			"data": {},
			"actions": [],
		}

	import erpnext

	company = erpnext.get_default_company() or frappe.db.get_value("Company", {"disabled": 0}, "name")
	qt = frappe.new_doc("Quotation")
	qt.quotation_to = "Customer"
	qt.party_name = customer
	qt.company = company

	for row in data.get("items") or []:
		item_code = row.get("item_code") or row.get("item_name")
		if not item_code:
			continue
		qt.append("items", {"item_code": item_code, "qty": flt(row.get("qty", 1))})

	if not qt.items:
		return {
			"status": "need_input",
			"message": _("Please specify item and quantity for the quotation."),
			"data": {},
			"actions": [],
		}

	qt.insert()
	return _created_response(qt)


def _execute_update(intent: dict, raw_message: str) -> dict:
	doctype = intent["doctype"]
	if not frappe.has_permission(doctype, "write"):
		return _permission_error()

	filters = dict(intent.get("filters") or {})
	data = intent.get("data") or {}

	if not data:
		return {
			"status": "need_input",
			"message": _("Please specify what to change (e.g. change name to XYZ)."),
			"data": {},
			"actions": [],
		}

	resolved, err = _resolve_intent_record(doctype, filters)
	if err:
		return err
	doc = frappe.get_doc(doctype, resolved)
	doc.update(data)
	doc.save()
	return {
		"status": "success",
		"message": _("{0} <b>{1}</b> updated successfully.").format(doctype, doc.name),
		"data": {"name": doc.name},
		"actions": [
			{"type": "open", "doctype": doctype, "name": doc.name, "label": _("Open {0}").format(doc.name)}
		],
	}


def _execute_delete(intent: dict, raw_message: str) -> dict:
	doctype = intent["doctype"]
	filters = dict(intent.get("filters") or {})

	if not frappe.has_permission(doctype, "delete"):
		return _permission_error()

	name, err = _resolve_intent_record(doctype, filters)
	if err:
		return err

	if not frappe.db.exists(doctype, name):
		return {
			"status": "error",
			"message": _("{0} <b>{1}</b> does not exist.").format(doctype, name),
			"data": {},
			"actions": [],
		}

	frappe.delete_doc(doctype, name)
	return {
		"status": "warning",
		"message": _("{0} <b>{1}</b> has been deleted.").format(doctype, name),
		"data": {"name": name},
		"actions": [],
	}


def _execute_report(intent: dict, raw_message: str) -> dict:
	doctype = intent.get("doctype") or "Sales Invoice"
	if not frappe.has_permission(doctype, "read"):
		return _permission_error()

	filters = _prepare_filters(intent.get("filters") or {}, doctype)
	config = get_config(doctype)
	amount_field = config.get("amount_field")

	if amount_field:
		rows = frappe.get_all(
			doctype,
			filters=filters,
			fields=[amount_field],
		)
		total = sum(flt(r.get(amount_field)) for r in rows)
		count = len(rows)
		currency = frappe.db.get_default("currency")
		return {
			"status": "success",
			"message": _(
				"<b>{0}</b> report: {1} record(s), total {2}."
			).format(
				intent.get("report_type", "summary"),
				count,
				fmt_money(total, currency=currency),
			),
			"data": {"count": count, "total": total},
			"actions": [],
		}

	count = frappe.db.count(doctype, filters)
	return {
		"status": "success",
		"message": _("Report: <b>{0}</b> {1} record(s).").format(count, doctype),
		"data": {"count": count},
		"actions": [],
	}


def _execute_analyze(intent: dict, raw_message: str) -> dict:
	doctype = intent.get("doctype") or "Sales Invoice"
	if not frappe.has_permission(doctype, "read"):
		return _permission_error()

	config = get_config(doctype)
	date_field = config.get("date_field") or "creation"
	amount_field = config.get("amount_field")

	from frappe.utils import get_first_day, get_last_day

	today = getdate(nowdate())
	filters = {date_field: ["between", [get_first_day(today), get_last_day(today)]]}

	count = frappe.db.count(doctype, filters)
	total = 0
	if amount_field:
		rows = frappe.get_all(doctype, filters=filters, fields=[amount_field])
		total = sum(flt(r.get(amount_field)) for r in rows)

	currency = frappe.db.get_default("currency")
	return {
		"status": "success",
		"message": _(
			"Monthly analysis for <b>{0}</b>: {1} record(s), total {2} this month."
		).format(doctype, count, fmt_money(total, currency=currency) if amount_field else "—"),
		"data": {"count": count, "total": total},
		"actions": [],
	}


def _execute_summarize(intent: dict, raw_message: str) -> dict:
	doctype = intent.get("doctype")
	if not doctype:
		return {
			"status": "need_input",
			"message": _("Please specify a document type to summarize."),
			"data": {},
			"actions": [],
		}

	if not frappe.has_permission(doctype, "read"):
		return _permission_error()

	total = frappe.db.count(doctype)
	recent = get_recent_records(doctype, 3)
	names = ", ".join(r["name"] for r in recent) if recent else _("none")
	return {
		"status": "success",
		"message": _(
			"<b>{0}</b> summary: {1} total record(s). Recent: {2}."
		).format(doctype, total, names),
		"data": {"total": total, "recent": recent},
		"actions": [],
	}


def _execute_submit(intent: dict, raw_message: str) -> dict:
	doctype = intent["doctype"]
	name = (intent.get("filters") or {}).get("name")
	if not name:
		return {
			"status": "need_input",
			"message": _("Please specify the document name to submit."),
			"data": {},
			"actions": [],
		}

	if not frappe.has_permission(doctype, "submit"):
		return _permission_error()

	doc = frappe.get_doc(doctype, name)
	doc.submit()
	log_action("approve", doctype, name)
	return {
		"status": "success",
		"message": _("{0} <b>{1}</b> approved successfully.").format(doctype, name),
		"data": {"name": name},
		"actions": [
			{"type": "open", "doctype": doctype, "name": name, "label": _("Open {0}").format(name)}
		],
	}


def _execute_reject(intent: dict, raw_message: str) -> dict:
	doctype = intent["doctype"]
	name = (intent.get("filters") or {}).get("name")
	if not name:
		return {
			"status": "need_input",
			"message": _("Please specify the document name to reject."),
			"data": {},
			"actions": [],
		}

	if not frappe.has_permission(doctype, "write"):
		return _permission_error()

	doc = frappe.get_doc(doctype, name)
	if doctype == "Leave Application" and hasattr(doc, "status"):
		doc.status = "Rejected"
		doc.save()
		log_action("reject", doctype, name)
		return {
			"status": "success",
			"message": _("Leave Application <b>{0}</b> rejected.").format(name),
			"data": {"name": name},
			"actions": [
				{"type": "open", "doctype": doctype, "name": name, "label": _("Open {0}").format(name)}
			],
		}

	if frappe.has_permission(doctype, "cancel") and doc.docstatus == 1:
		doc.cancel()
		log_action("reject", doctype, name)
		return {
			"status": "warning",
			"message": _("{0} <b>{1}</b> cancelled/rejected.").format(doctype, name),
			"data": {"name": name},
			"actions": [],
		}

	return {
		"status": "need_input",
		"message": _("Cannot reject {0} {1}. Open the document to use workflow actions.").format(
			doctype, name
		),
		"data": {},
		"actions": [
			{"type": "open", "doctype": doctype, "name": name, "label": _("Open {0}").format(name)}
		],
	}


def _execute_cancel_doc(intent: dict, raw_message: str) -> dict:
	doctype = intent["doctype"]
	name = (intent.get("filters") or {}).get("name")
	if not name:
		return {
			"status": "need_input",
			"message": _("Please specify the document name to cancel."),
			"data": {},
			"actions": [],
		}

	if not frappe.has_permission(doctype, "cancel"):
		return _permission_error()

	doc = frappe.get_doc(doctype, name)
	doc.cancel()
	log_action("cancel", doctype, name)
	return {
		"status": "warning",
		"message": _("{0} <b>{1}</b> cancelled.").format(doctype, name),
		"data": {"name": name},
		"actions": [],
	}


def _execute_email(intent: dict, raw_message: str) -> dict:
	return {
		"status": "need_input",
		"message": _("Email sending from AI Bot is not configured yet. Open the document and use Email."),
		"data": {},
		"actions": [],
	}


def _execute_notify(intent: dict, raw_message: str) -> dict:
	return {
		"status": "need_input",
		"message": _("Use ERPNext notifications or assign a task to notify users."),
		"data": {},
		"actions": [],
	}


def _prepare_filters(filters: dict, doctype: str) -> dict:
	"""Convert copilot filters to frappe.get_list compatible filters."""
	result = {}
	config = get_config(doctype)
	amount_field = config.get("amount_field")

	for key, val in filters.items():
		field = key
		if key == "grand_total" and amount_field and amount_field != "grand_total":
			field = amount_field
		result[field] = val

	return result


def _format_record_line(doctype: str, record: dict, fields: list) -> str:
	parts = [f"<b>{record['name']}</b>"]
	for f in fields:
		if f != "name" and record.get(f) is not None:
			parts.append(str(record[f]))
	return " — ".join(parts)


def _created_response(doc) -> dict:
	return {
		"status": "success",
		"message": _("{0} <b>{1}</b> created successfully.").format(doc.doctype, doc.name),
		"data": {"name": doc.name},
		"actions": [
			{
				"type": "open",
				"doctype": doc.doctype,
				"name": doc.name,
				"label": _("Open {0}").format(doc.name),
			}
		],
	}


def _permission_error() -> dict:
	return {
		"status": "error",
		"message": _("You do not have permission for this operation."),
		"data": {},
		"actions": [],
	}


def _execute_site_search(intent: dict) -> dict:
	query = intent.get("search_query") or ""
	doctype = intent.get("doctype")

	if doctype:
		if not frappe.has_permission(doctype, "read"):
			return _permission_error()
		records = search_in_doctype(doctype, query, limit=10)
		if not records:
			return {
				"status": "success",
				"message": _("No <b>{0}</b> records found for <i>{1}</i>.").format(
					doctype, frappe.utils.escape_html(query)
				),
				"data": {},
				"actions": [],
			}
		from ai_bot.services.site_data import format_record_lines

		lines = format_record_lines(doctype, records)
		return {
			"status": "success",
			"message": _("<p>Matches in <b>{0}</b>:</p><ul>{1}</ul>").format(
				doctype, "".join(f"<li>{line}</li>" for line in lines)
			),
			"data": {"records": records},
			"actions": [
				{"type": "open", "doctype": doctype, "name": r["name"], "label": r["name"]}
				for r in records[:5]
			],
		}

	results = search_site_wide(query, max_doctypes=8, per_limit=4)
	if not results:
		return {
			"status": "success",
			"message": _("No records found for <i>{0}</i> across your accessible data.").format(
				frappe.utils.escape_html(query)
			),
			"data": {},
			"actions": [],
		}

	# One exact name match — show detail
	if len(results) == 1 and len(results[0]["records"]) == 1:
		rec = results[0]["records"][0]
		dt = results[0]["doctype"]
		summary = get_record_summary(dt, rec["name"])
		if summary:
			return {
				"status": "success",
				"message": format_record_detail(summary),
				"data": {"name": rec["name"], "doctype": dt},
				"actions": [
					{"type": "open", "doctype": dt, "name": rec["name"], "label": _("Open {0}").format(rec["name"])}
				],
			}

	return {
		"status": "success",
		"message": format_search_results(results),
		"data": {"results": results},
		"actions": [
			{
				"type": "open",
				"doctype": block["doctype"],
				"name": block["records"][0]["name"],
				"label": block["records"][0]["name"],
			}
			for block in results[:5]
			if block.get("records")
		],
	}


def _execute_record_detail(intent: dict) -> dict:
	doctype = intent.get("doctype")
	name = (intent.get("filters") or {}).get("name")

	if not doctype or not name:
		hint = (intent.get("filters") or {}).get("_hint")
		if doctype and hint:
			name = resolve_record(doctype, hint)
		if not name:
			return {
				"status": "need_input",
				"message": _("Please specify which record to show."),
				"data": {},
				"actions": [],
			}

	if not frappe.has_permission(doctype, "read"):
		return _permission_error()

	summary = get_record_summary(doctype, name)
	if not summary:
		return {
			"status": "error",
			"message": _("{0} <b>{1}</b> not found or no access.").format(doctype, name),
			"data": {},
			"actions": [],
		}

	return {
		"status": "success",
		"message": format_record_detail(summary),
		"data": {"name": name, "doctype": doctype},
		"actions": [
			{"type": "open", "doctype": doctype, "name": name, "label": _("Open {0}").format(name)}
		],
	}


def _sort_intents_for_execution(intents: list[dict]) -> list[dict]:
	"""Run updates before deletes when both appear (safer for rename-then-delete)."""
	order = {"update": 0, "create": 1, "read": 2, "approve": 3, "report": 4, "delete": 9, "cancel": 9}

	return sorted(intents, key=lambda i: order.get(i.get("action"), 5))


def _resolve_intent_record(doctype: str, filters: dict) -> tuple[str | None, dict | None]:
	"""Resolve document name from filters, hints, or customer_name."""
	filters = dict(filters)
	hint = filters.pop("_hint", None)

	if filters.get("name"):
		return filters["name"], None

	if filters.get("customer_name"):
		name = frappe.db.get_value(doctype, {"customer_name": filters["customer_name"]}, "name")
		if name:
			return name, None
		return None, {
			"status": "error",
			"message": _("No {0} found matching <b>{1}</b>.").format(
				doctype, filters["customer_name"]
			),
			"data": {},
			"actions": [],
		}

	if hint:
		name = resolve_record(doctype, hint)
		if name:
			return name, None
		return None, {
			"status": "error",
			"message": _("No {0} found matching <b>{1}</b>.").format(doctype, hint),
			"data": {},
			"actions": [],
		}

	return None, {
		"status": "need_input",
		"message": _("Please specify which {0} record (name or title).").format(doctype),
		"data": {},
		"actions": [],
	}
