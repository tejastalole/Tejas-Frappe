frappe.ui.form.on("Attendance Log", {
	refresh(frm) {
		if (frm.is_new()) {
			gym_management.geo.get_location((coords) => {
				if (coords) {
					frm.set_value("check_in_latitude", coords.latitude);
					frm.set_value("check_in_longitude", coords.longitude);
				}
			});
			return;
		}

		if (!frm.doc.check_out_time) {
			frm.add_custom_button(__("Check Out"), () => {
				gym_management.geo.with_location((geo) => {
					frappe.call({
						method: "gym_management.gym_management.doctype.attendance_log.attendance_log.check_out",
						args: { attendance_log: frm.doc.name, ...geo },
						freeze: true,
						callback(r) {
							if (!r.exc) {
								frappe.show_alert({
									message: r.message.message || __("Checked out"),
									indicator: "green",
								});
								frm.reload_doc();
							}
						},
					});
				});
			});
		}
	},
});
