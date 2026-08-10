frappe.ui.form.on("Bulk Data Tool", {
	refresh(frm) {
		frm.disable_save();

		frm.add_custom_button(__("Count Records"), () => {
			call_action(frm, "count_records");
		});

		frm.add_custom_button(__("Preview Sample"), () => {
			call_action(frm, "preview_records");
		});

		frm.add_custom_button(__("Export Names (CSV)"), () => {
			call_action(frm, "export_names");
		});

		frm.add_custom_button(
			__("Delete All Matching"),
			() => {
				const count = frm.doc.record_count || "?";
				frappe.confirm(
					__(
						"Delete all matching records in <b>{0}</b>?<br>Estimated count: <b>{1}</b><br><br>This cannot be easily undone.",
						[frm.doc.target_doctype, count]
					),
					() => call_action(frm, "delete_records")
				);
			},
			__("Danger Zone")
		);

		frm.add_custom_button(
			__("Clear Recycle Bin for DocType"),
			() => {
				frappe.confirm(
					__("Permanently remove deleted {0} docs from Recycle Bin?", [
						frm.doc.target_doctype,
					]),
					() => call_action(frm, "clear_recycle_bin")
				);
			},
			__("Danger Zone")
		);
	},

	target_doctype(frm) {
		if (frm.doc.target_doctype) {
			call_action(frm, "count_records", false);
		}
	},
});

function call_action(frm, action, freeze = true) {
	if (!frm.doc.target_doctype) {
		frappe.msgprint(__("Please select a DocType first."));
		return;
	}

	frappe.call({
		method: "bulk_data_tools.api.run_action",
		args: {
			action: action,
			target_doctype: frm.doc.target_doctype,
			filters_json: frm.doc.filters_json || "[]",
			docstatus_filter: frm.doc.docstatus_filter || "All",
			batch_size: frm.doc.batch_size || 100,
			force_delete: frm.doc.force_delete ? 1 : 0,
			delete_permanently: frm.doc.delete_permanently ? 1 : 0,
			dry_run: frm.doc.dry_run ? 1 : 0,
			confirm_text: frm.doc.confirm_text || "",
		},
		freeze: freeze,
		freeze_message: __("Working..."),
		callback(r) {
			if (r.exc) return;
			const result = r.message || {};
			if (typeof result.count !== "undefined") {
				frm.set_value("record_count", result.count);
			}
			frm.set_value("last_result", JSON.stringify(result, null, 2));
			frm.refresh_field("record_count");
			frm.refresh_field("last_result");

			if (result.download_url) {
				window.open(result.download_url, "_blank");
			}

			frappe.show_alert({
				message: result.message || __("Done"),
				indicator: result.ok === false ? "red" : "green",
			});
		},
	});
}
