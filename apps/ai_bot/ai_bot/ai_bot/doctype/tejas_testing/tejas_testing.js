// Copyright (c) 2026, Tejas and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tejas Testing", {
	refresh(frm) {
		frm.add_custom_button(__("Create"), () => {
			if (frm.is_new()) {
				frm.save();
			} else {
				frappe.new_doc("Tejas Testing");
			}
		});
	},
});
