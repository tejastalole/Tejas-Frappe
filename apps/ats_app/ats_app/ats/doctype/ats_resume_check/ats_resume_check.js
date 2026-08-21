frappe.ui.form.on("ATS Resume Check", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Check ATS Score"), () => {
			frappe.call({
				method: "ats_app.ats.scoring.check_ats_score",
				args: { name: frm.doc.name },
				freeze: true,
				freeze_message: __("Analyzing resume..."),
				callback(r) {
					frm.reload_doc();
					if (r.message) {
						frappe.msgprint({
							title: __("ATS Score"),
							indicator: "green",
							message: __(
								"<b>Score: {0} / 100</b><br>{1}",
								[r.message.ats_score, r.message.recommendation]
							),
						});
					}
				},
			});
		}).addClass("btn-primary");
	},
});
