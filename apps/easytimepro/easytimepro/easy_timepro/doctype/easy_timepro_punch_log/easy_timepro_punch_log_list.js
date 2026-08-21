frappe.listview_settings["Easy TimePro Punch Log"] = {
	hide_name_column: true,
	hide_name_filter: true,
	onload(listview) {
		// Force white list background (remove any green/mint tint)
		if (!document.getElementById("etp-punch-log-bg-fix")) {
			const style = document.createElement("style");
			style.id = "etp-punch-log-bg-fix";
			style.textContent = `
				body.etp-glass-workspace { /* clear leaked workspace class on this page */ }
				.page-container[data-page-route*="Easy TimePro Punch Log"] .layout-main-section,
				.desk-page[data-page-route*="Easy TimePro Punch Log"] .layout-main-section,
				[id*="Easy-TimePro-Punch-Log"] .layout-main-section,
				.frappe-list,
				.frappe-list .result,
				.frappe-list-area,
				.list-paging-area,
				.page-form,
				.layout-main-section .frappe-card,
				.list-container,
				div[data-page-container] .layout-main-section-wrapper,
				div[data-page-container] .layout-main-section {
					background: #ffffff !important;
					background-color: #ffffff !important;
					background-image: none !important;
				}
				.list-row, .list-row-container, .list-row-head {
					background: transparent !important;
				}
			`;
			document.head.appendChild(style);
		}
		document.body.classList.remove("etp-glass-workspace");

		listview.page.add_inner_button(__("Sync Now"), () => {
			frappe.call({
				method: "easytimepro.easy_timepro.doctype.easy_timepro_settings.easy_timepro_settings.sync_now",
				freeze: true,
				freeze_message: __("Fetching latest punches..."),
				callback(r) {
					listview.refresh();
					if (r.message) {
						frappe.show_alert({
							message: __(
								"Fetched: {0}, Created: {1}, Skipped: {2}",
								[r.message.fetched, r.message.created, r.message.skipped]
							),
							indicator: "blue",
						});
					}
				},
			});
		});

		const start_auto_sync = (interval_seconds) => {
			const ms = Math.max(5, interval_seconds || 5) * 1000;
			if (listview._etp_refresh_timer) {
				clearInterval(listview._etp_refresh_timer);
			}
			listview._etp_refresh_timer = setInterval(() => {
				if (!(cur_list && cur_list.doctype === "Easy TimePro Punch Log")) {
					clearInterval(listview._etp_refresh_timer);
					listview._etp_refresh_timer = null;
					return;
				}
				// Only auto-sync when Enable Sync is on
				frappe.db.get_single_value("Easy TimePro Settings", "enabled").then((enabled) => {
					if (!enabled) return;
					frappe.call({
						method: "easytimepro.easy_timepro.doctype.easy_timepro_settings.easy_timepro_settings.sync_now",
						callback(r) {
							if (r.message && r.message.created > 0 && cur_list) {
								cur_list.refresh();
								frappe.show_alert({
									message: __("{0} new punch(es) synced", [r.message.created]),
									indicator: "blue",
								});
							}
						},
					});
				});
			}, ms);
		};

		frappe.call({
			method: "easytimepro.easy_timepro.doctype.easy_timepro_settings.easy_timepro_settings.get_sync_interval_seconds",
			callback(r) {
				start_auto_sync(r.message || 5);
			},
		});
	},
};
