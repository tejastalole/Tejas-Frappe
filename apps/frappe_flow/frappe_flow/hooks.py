app_name = "frappe_flow"
app_title = "Frappe Flow"
app_publisher = "Tejas"
app_description = "No-code automation builder — Zapier-style workflows for Frappe and ERPNext"
app_email = "hello@tejas.com"
app_license = "mit"

required_apps = ["frappe", "erpnext"]

app_include_js = "/assets/frappe_flow/js/flow_form_actions.js"

doc_events = {
	"*": {
		"after_insert": "frappe_flow.engine.executor.handle_doc_event",
		"on_update": "frappe_flow.engine.executor.handle_doc_event",
		"on_submit": "frappe_flow.engine.executor.handle_doc_event",
		"on_cancel": "frappe_flow.engine.executor.handle_doc_event",
	}
}

scheduler_events = {
	"hourly": [
		"frappe_flow.engine.scheduler.run_hourly_flows",
		"frappe_flow.engine.delay.process_delayed_steps",
	],
	"daily": [
		"frappe_flow.engine.scheduler.run_daily_flows",
	],
	"weekly": [
		"frappe_flow.engine.scheduler.run_weekly_flows",
	],
	"monthly": [
		"frappe_flow.engine.scheduler.run_monthly_flows",
	],
}

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["Flow Admin", "Flow Designer", "Flow User"]]],
	},
	{
		"dt": "FF Flow Template",
		"filters": [["template_name", "in", ["CRM Lead Welcome Pack", "Sales Quotation Follow-up Pack", "HR Employee Onboarding Pack"]]],
	},
]

doctype_js = {
	"FF Flow Automation": "public/js/ff_flow_automation.js",
	"FF Flow Credential": "public/js/ff_flow_credential.js",
}
