frappe.ui.form.on("Easy TimePro Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), () => {
			frappe.call({
				method: "easytimepro.easy_timepro.doctype.easy_timepro_settings.easy_timepro_settings.test_connection",
				freeze: true,
				callback(r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Connection"),
							indicator: "green",
							message: r.message.message,
						});
					}
				},
			});
		});

		frm.add_custom_button(__("Sync Now"), () => {
			frappe.call({
				method: "easytimepro.easy_timepro.doctype.easy_timepro_settings.easy_timepro_settings.sync_now",
				freeze: true,
				freeze_message: __("Fetching punches from Easy TimePro..."),
				callback(r) {
					frm.reload_doc();
					if (r.message) {
						frappe.msgprint({
							title: __("Sync Complete"),
							indicator: "green",
							message: __(
								"Fetched: {0}, Created: {1}, Skipped: {2}",
								[r.message.fetched, r.message.created, r.message.skipped]
							),
						});
					}
				},
			});
		}).addClass("btn-primary");

		frm.add_custom_button(__("Sync Employee IDs"), () => {
			frappe.call({
				method: "easytimepro.easy_timepro.doctype.easy_timepro_settings.easy_timepro_settings.sync_employee_ids",
				freeze: true,
				freeze_message: __("Matching Easy TimePro Employee IDs to Employees..."),
				callback(r) {
					if (!r.message) return;
					const m = r.message;
					frappe.msgprint({
						title: __("Employee ID Sync"),
						indicator: "green",
						message: __(
							"Updated device IDs: {0}. Remapped punches: {1}. Unmatched: {2}.",
							[
								(m.updated || []).length,
								m.punch_logs_updated || 0,
								(m.unmatched || []).length,
							]
						),
					});
				},
			});
		});
	},
});
