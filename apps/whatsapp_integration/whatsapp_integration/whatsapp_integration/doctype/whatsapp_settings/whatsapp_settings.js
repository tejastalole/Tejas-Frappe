frappe.ui.form.on("WhatsApp Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Send Test Message"), () => {
			frappe.prompt(
				[
					{
						fieldname: "to",
						label: __("Recipient (with country code)"),
						fieldtype: "Data",
						reqd: 1,
						description: __("Example: 919876543210"),
					},
					{
						fieldname: "message",
						label: __("Message"),
						fieldtype: "Small Text",
						reqd: 1,
						default: "Hello from Frappe WhatsApp Integration",
					},
				],
				(values) => {
					frappe.call({
						method: "whatsapp_integration.api.message.send_whatsapp_message",
						args: values,
						freeze: true,
						freeze_message: __("Sending..."),
						callback(r) {
							if (!r.exc) {
								frappe.show_alert({
									message: __("Message queued / sent"),
									indicator: "green",
								});
							}
						},
					});
				},
				__("Send Test WhatsApp Message"),
				__("Send")
			);
		});
	},
});
