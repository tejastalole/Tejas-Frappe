frappe.ui.form.on("DWB Approval Rule", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Visual Builder"), () => {
				frappe.set_route("workflow-builder", frm.doc.name);
			});
		}
	},
});
