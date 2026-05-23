// Copyright (c) 2026, Tejas and contributors
// MIT License

frappe.ui.form.on("AI Bot Settings", {
	refresh(frm) {
		frm.set_intro(__("Configure AI ERP Copilot behavior, optional LLM, and security logging."));
	},
});
