frappe.ui.form.on("BOQ Item Master", {
	setup(frm) {
		frm.set_query("boq_sub_category", () => {
			if (frm.doc.boq_category) {
				return { filters: { boq_category: frm.doc.boq_category, is_active: 1 } };
			}
		});
	},

	boq_category(frm) {
		frm.set_value("boq_sub_category", "");
	},
});
