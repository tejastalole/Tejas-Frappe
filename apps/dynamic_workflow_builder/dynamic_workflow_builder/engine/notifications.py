# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.utils import now_datetime

from dynamic_workflow_builder.utils import resolve_email_recipients


def create_approval_log(
	approval_request=None,
	reference_doctype=None,
	reference_name=None,
	user=None,
	action=None,
	comments=None,
):
	frappe.get_doc(
		{
			"doctype": "DWB Approval Log",
			"approval_request": approval_request,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"user": user or frappe.session.user,
			"action": action,
			"comments": comments,
			"timestamp": now_datetime(),
		}
	).insert(ignore_permissions=True)


def notify_approver(request_doc, subject=None, message=None):
	if not request_doc.assigned_to:
		return

	subject = subject or frappe._("Approval pending for {0} {1}").format(
		request_doc.reference_doctype, request_doc.reference_name
	)
	message = message or frappe._(
		"{0} {1} requires your approval. Open Approval Center to review."
	).format(request_doc.reference_doctype, request_doc.reference_name)

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"subject": subject,
			"email_content": message,
			"for_user": request_doc.assigned_to,
			"type": "Alert",
			"document_type": request_doc.reference_doctype,
			"document_name": request_doc.reference_name,
		}
	).insert(ignore_permissions=True)

	try:
		recipients = resolve_email_recipients(request_doc.assigned_to)
		if recipients:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				now=True,
			)
	except Exception:
		frappe.log_error(title="DWB Approval Email Failed")
