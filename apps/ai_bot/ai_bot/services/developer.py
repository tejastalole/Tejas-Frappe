# Copyright (c) 2026, Tejas and contributors
# MIT License

"""Generate Frappe client/server script snippets from natural language."""

import re

from frappe import _


def generate_client_script(request: str, doctype: str | None = None) -> str:
	lower = request.lower()
	dt = doctype or "Your DocType"

	if "hide" in lower and "create" in lower and "reject" in lower:
		return f"""// Client Script — {dt}
frappe.ui.form.on("{dt}", {{
	refresh(frm) {{
		if (frm.doc.workflow_state === "Rejected") {{
			frm.page.btn_primary.hide();
		}}
	}}
}});"""

	if "read only" in lower or "readonly" in lower:
		return f"""// Client Script — {dt}
frappe.ui.form.on("{dt}", {{
	refresh(frm) {{
		if (frm.doc.docstatus === 1) {{
			frm.set_read_only();
		}}
	}}
}});"""

	if "validate" in lower:
		return f"""// Client Script — {dt}
frappe.ui.form.on("{dt}", {{
	validate(frm) {{
		// Add validation rules
	}}
}});"""

	return f"""// Client Script — {dt}
frappe.ui.form.on("{dt}", {{
	refresh(frm) {{
		// TODO: {request[:80]}
	}}
}});"""


def generate_server_script(request: str, doctype: str | None = None) -> str:
	dt = doctype or "Your DocType"
	if "before_save" in request.lower() or "validate" in request.lower():
		event = "before_save"
	else:
		event = "before_submit"

	return f"""# Server Script — {dt} ({event})
# event: {event}
# reference_doctype: {dt}

doc = frappe.get_doc(doc)
# TODO: {request[:80]}
"""


def generate_sql_hint(request: str) -> str:
	if "customer" in request.lower() and "sales" in request.lower():
		return """-- Top customers by sales (example)
SELECT customer_name, SUM(grand_total) AS total
FROM `tabSales Invoice`
WHERE docstatus = 1
GROUP BY customer_name
ORDER BY total DESC
LIMIT 10;"""

	return """-- Example: unpaid sales invoices
SELECT name, customer, outstanding_amount, posting_date
FROM `tabSales Invoice`
WHERE docstatus = 1 AND outstanding_amount > 0
ORDER BY posting_date DESC
LIMIT 20;"""


def match_developer_request(message: str) -> bool:
	lower = message.lower()
	return bool(
		re.search(
			r"\b(client script|server script|sql query|workflow|api integration|report script|generate script)\b",
			lower,
		)
	)
