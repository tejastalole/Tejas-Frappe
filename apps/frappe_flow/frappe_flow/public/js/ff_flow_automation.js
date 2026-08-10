frappe.ui.form.on("FF Flow Automation", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Flow Builder"), () => {
				frappe.set_route("flow-builder", frm.doc.name);
			});
			if (frm.doc.status === "Draft") {
				frm.add_custom_button(__("Activate"), () => {
					frm.set_value("status", "Active");
					frm.set_value("is_active", 1);
					frm.save();
				});
			}
		}
		frm.add_custom_button(__("AI Generate Flow"), () => {
			frappe.prompt(
				[{ fieldname: "prompt", fieldtype: "Small Text", label: __("Describe your automation"), reqd: 1 }],
				(values) => {
					frappe.call({
						method: "frappe_flow.api.flow.ai_generate_flow",
						args: { prompt: values.prompt },
						callback(r) {
							const data = r.message;
							if (data.flow_json) frm.set_value("flow_json", data.flow_json);
							if (data.document_type) frm.set_value("document_type", data.document_type);
							if (data.trigger_event) frm.set_value("trigger_event", data.trigger_event);
							if (data.trigger_type) frm.set_value("trigger_type", data.trigger_type);
							frappe.show_alert({ message: __("Flow generated — review and save"), indicator: "green" });
						},
					});
				},
				__("AI Flow Builder"),
				__("Generate")
			);
		}, __("Tools"));
	},
});
