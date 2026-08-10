frappe.ui.form.on("ZKTeco Device", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Test Connection"), () => {
			frm.call("test_connection").then((r) => {
				if (r.message && r.message.success) {
					frappe.msgprint({
						title: __("Connection successful"),
						indicator: "green",
						message: __(
							"Device: {0}<br>IP: {1}<br>Port: {2}<br>{3}",
							[
								r.message.device_info || frm.doc.device_name,
								frm.doc.ip_address,
								frm.doc.tcp_port,
								r.message.details || "",
							]
						),
					});
				} else {
					frappe.msgprint({
						title: __("Connection failed"),
						indicator: "red",
						message: (r.message && r.message.error) || __("Unknown error"),
					});
				}
				frm.reload_doc();
			});
		});

		frm.add_custom_button(__("Sync Now"), () => {
			frm.call("sync_now", { full_sync: 0 }).then((r) => show_sync_result(r.message));
		});

		frm.add_custom_button(__("Full Sync"), () => {
			frappe.confirm(__("Download all attendance logs from the device?"), () => {
				frm.call("sync_now", { full_sync: 1 }).then((r) => show_sync_result(r.message));
			});
		});

		frm.add_custom_button(__("Clear Error"), () => {
			frm.call("clear_error").then(() => frm.reload_doc());
		});
	},
});

function show_sync_result(msg) {
	if (!msg) return;
	const m = msg;
	frappe.msgprint({
		title: __("Attendance Sync Completed"),
		indicator: m.status === "Failed" ? "red" : "green",
		message: __(
			"Device: {0}<br>Total records: {1}<br>New records: {2}<br>Duplicate records: {3}<br>Failed records: {4}",
			[m.device || "", m.total_records || 0, m.new_records || 0, m.duplicate_records || 0, m.failed_records || 0]
		),
	});
	cur_frm && cur_frm.reload_doc();
}
