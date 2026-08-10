frappe.ui.form.on("FF Flow Credential", {
	refresh(frm) {
		frm.set_intro(
			__(
				"Twilio: API Key = Account SID, API Secret = Auth Token, Config JSON = " +
					'{"from_number": "whatsapp:+14155238886"}. ' +
					"Meta: API Key = Access Token, Config JSON = " +
					'{"phone_number_id": "YOUR_PHONE_NUMBER_ID"}.'
			),
			"blue"
		);
	},
});
