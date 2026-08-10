frappe.ui.form.on("Biometric Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Pull From Devices Now"), () => {
			frappe.call({
				method: "biometric_integration.api.pull_now",
				freeze: true,
				freeze_message: __("Pulling attendance via TCP 4370..."),
				callback(r) {
					if (!r.exc) {
						frm.reload_doc();
						frappe.msgprint({
							title: __("Pull Complete"),
							indicator: "green",
							message: __(
								"Downloaded: {0}<br>Inserted: {1}<br>Skipped: {2}",
								[
									(r.message && r.message.downloaded) || 0,
									(r.message && r.message.inserted) || 0,
									(r.message && r.message.skipped) || 0,
								]
							),
						});
					}
				},
			});
		});
	},
});
