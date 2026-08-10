frappe.ui.form.on("Gym Member", {
	refresh(frm) {
		if (frm.is_new()) return;

		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Attendance Log",
				filters: {
					gym_member: frm.doc.name,
					attendance_date: frappe.datetime.get_today(),
				},
				fieldname: ["name", "check_in_time", "check_out_time"],
			},
			callback(r) {
				const att = r.message;
				const can_check_in = !att || !att.check_in_time;
				const can_check_out =
					att && att.check_in_time && !att.check_out_time;

				if (can_check_in) {
					frm.add_custom_button(__("Check In"), () => {
						gym_management.geo.with_location((geo) => {
							frappe.call({
								method:
									"gym_management.gym_management.doctype.gym_member.gym_member.check_in_member",
								args: { gym_member: frm.doc.name, ...geo },
								freeze: true,
								callback(res) {
									if (!res.exc) {
										frappe.show_alert({
											message:
												res.message.message || __("Checked in"),
											indicator: "green",
										});
										frm.refresh();
									}
								},
							});
						});
					});
				}

				if (can_check_out) {
					frm.add_custom_button(__("Check Out"), () => {
						gym_management.geo.with_location((geo) => {
							frappe.call({
								method:
									"gym_management.gym_management.doctype.attendance_log.attendance_log.check_out",
								args: { attendance_log: att.name, ...geo },
								freeze: true,
								callback(res) {
									if (!res.exc) {
										frappe.show_alert({
											message:
												res.message.message || __("Checked out"),
											indicator: "green",
										});
										frm.refresh();
									}
								},
							});
						});
					});
				}
			},
		});

		frm.add_custom_button(__("New Membership"), () => {
			frappe.new_doc("Gym Membership", {
				gym_member: frm.doc.name,
			});
		});

		frm.add_custom_button(__("Attendance"), () => {
			frappe.set_route("List", "Attendance Log", {
				gym_member: frm.doc.name,
			});
		});
	},
});
