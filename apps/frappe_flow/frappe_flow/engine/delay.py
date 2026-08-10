# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import now_datetime

from frappe_flow.engine.executor import execute_flow


def process_delayed_steps():
	pending = frappe.get_all(
		"FF Flow Delay Queue",
		filters={"status": "Pending", "run_at": ["<=", now_datetime()]},
		fields=["name", "flow", "execution", "resume_node_id", "reference_doctype", "reference_name", "context_json"],
		limit=50,
	)
	for row in pending:
		try:
			doc = None
			if row.reference_doctype and row.reference_name:
				doc = frappe.get_doc(row.reference_doctype, row.reference_name)
			context = row.context_json if isinstance(row.context_json, dict) else {}
			execute_flow(
				row.flow,
				doc=doc,
				context=context,
				resume_node_id=row.resume_node_id,
				execution_name=row.execution,
			)
			frappe.db.set_value("FF Flow Delay Queue", row.name, "status", "Completed")
		except Exception:
			frappe.log_error(title=f"FF Flow delay resume failed: {row.name}")
