frappe.ui.form.on("Biometric Device", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.ip_address) {
			frm.add_custom_button(__("Test TCP Connection"), () => {
				frappe.call({
					method: "biometric_integration.api.test_device_connection",
					args: { device: frm.doc.name },
					freeze: true,
					callback(r) {
						if (!r.exc) {
							frappe.msgprint({
								title: __("Connection Test"),
								indicator: r.message && r.message.success ? "green" : "red",
								message: JSON.stringify(r.message || {}, null, 2),
							});
						}
					},
				});
			});

			frm.add_custom_button(__("Pull Attendance"), () => {
				frappe.call({
					method: "biometric_integration.api.pull_device",
					args: { device: frm.doc.name },
					freeze: true,
					freeze_message: __("Pulling from device..."),
					callback(r) {
						if (!r.exc) {
							frm.reload_doc();
							frappe.show_alert({
								message: __("Pull finished"),
								indicator: "green",
							});
						}
					},
				});
			});
		}
	},
});
