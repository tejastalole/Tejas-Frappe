frappe.ui.form.on("Gym Member", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Check In"), () => {
			gym_management.geo.with_location((geo) => {
				frappe.call({
					method: "gym_management.gym_management.doctype.gym_member.gym_member.check_in_member",
					args: { gym_member: frm.doc.name, ...geo },
					freeze: true,
					callback(r) {
						if (!r.exc) {
							frappe.show_alert({
								message: r.message.message || __("Checked in"),
								indicator: "green",
							});
						}
					},
				});
			});
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
