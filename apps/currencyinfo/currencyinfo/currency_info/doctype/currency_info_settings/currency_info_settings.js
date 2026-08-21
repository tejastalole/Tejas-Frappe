// Copyright (c) 2026, Tejas and contributors
// MIT License

frappe.ui.form.on("Currency Info Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Open Live Feed"), () => {
			frappe.set_route("currency-info-live");
		});
		frm.add_custom_button(__("Restart Stream"), () => {
			frappe.call({
				method: "currencyinfo.currency_info.stream.restart_stream",
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Stream restart requested"), indicator: "blue" });
					frm.reload_doc();
				},
			});
		});
	},
});
