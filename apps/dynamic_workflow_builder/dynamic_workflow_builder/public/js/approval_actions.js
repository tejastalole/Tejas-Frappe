frappe.provide("dynamic_workflow_builder");

dynamic_workflow_builder.inject_approval_buttons = function (frm) {
	if (frm.is_new() || frm.doc.doctype.startsWith("DWB ")) return;

	frappe.call({
		method: "dynamic_workflow_builder.api.dashboard.get_document_approval",
		args: { doctype: frm.doc.doctype, docname: frm.doc.name },
		callback(r) {
			const approval = r.message;
			if (!approval) return;
			if (approval.assigned_to !== frappe.session.user && !frappe.user.has_role("System Manager")) {
				frm.dashboard.add_comment(
					__("Pending approval with {0} (Level {1})", [
						approval.assigned_to,
						approval.current_level,
					]),
					"blue",
					true
				);
				return;
			}

			frm.dashboard.set_headline_alert(
				__(
					"Approval pending — Level {0} · SLA: {1}",
					[approval.current_level, approval.sla_status]
				),
				"orange"
			);

			frm.add_custom_button(__("Approve"), () => dynamic_workflow_builder.act(approval.name, "approve"), __("Approval"));
			frm.add_custom_button(__("Reject"), () => dynamic_workflow_builder.act(approval.name, "reject"), __("Approval"));
			frm.add_custom_button(
				__("Delegate"),
				() => dynamic_workflow_builder.delegate(approval.name),
				__("Approval")
			);
			frm.add_custom_button(
				__("Request Changes"),
				() => dynamic_workflow_builder.act(approval.name, "request_changes"),
				__("Approval")
			);
		},
	});
};

dynamic_workflow_builder.act = function (name, action) {
	const prompts = {
		approve: { method: "dynamic_workflow_builder.engine.processor.approve_request", label: __("Comments") },
		reject: { method: "dynamic_workflow_builder.engine.processor.reject_request", label: __("Rejection Reason") },
		request_changes: {
			method: "dynamic_workflow_builder.engine.processor.request_changes",
			label: __("Change Request"),
		},
	};
	const cfg = prompts[action];
	frappe.prompt(
		[{ fieldname: "comments", fieldtype: "Small Text", label: cfg.label }],
		(values) => {
			frappe.call({
				method: cfg.method,
				args: { name, comments: values.comments },
				callback() {
					frappe.show_alert({ message: __("Done"), indicator: "green" });
					cur_frm.reload_doc();
				},
			});
		},
		__(action.replace("_", " ").toUpperCase()),
		__("Submit")
	);
};

dynamic_workflow_builder.delegate = function (name) {
	frappe.prompt(
		[
			{ fieldname: "delegate_to", fieldtype: "Link", options: "User", label: __("Delegate To"), reqd: 1 },
			{ fieldname: "comments", fieldtype: "Small Text", label: __("Comments") },
		],
		(values) => {
			frappe.call({
				method: "dynamic_workflow_builder.engine.processor.delegate_request",
				args: { name, ...values },
				callback() {
					frappe.show_alert({ message: __("Delegated"), indicator: "green" });
					cur_frm.reload_doc();
				},
			});
		},
		__("Delegate Approval"),
		__("Delegate")
	);
};

$(document).on("form-refresh", function (_e, frm) {
	if (frm && frm.doctype) {
		dynamic_workflow_builder.inject_approval_buttons(frm);
	}
});
