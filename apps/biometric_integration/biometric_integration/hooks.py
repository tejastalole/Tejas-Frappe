app_name = "biometric_integration"
app_title = "Biometric Integration"
app_publisher = "Tejas"
app_description = "ADMS / ZKTeco biometric device integration for Frappe / ERPNext"
app_email = "hello@tejas.com"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["erpnext"]

after_install = "biometric_integration.install.after_install"
after_migrate = "biometric_integration.install.after_migrate"

# SenseFace / ZKTeco ADMS Cloud Server paths: /iclock/cdata, /iclock/getrequest, ...
page_renderer = [
	"biometric_integration.renderers.ZKTecoADMSRenderer",
]

scheduler_events = {
	"cron": {
		"*/10 * * * *": [
			"biometric_integration.scheduler.pull_attendance"
		]
	}
}

app_include_js = "/assets/biometric_integration/js/workspace_link_counts.js"

doctype_list_js = {
	"Biometric Check In Check Out": "biometric_integration/doctype/biometric_check_in_check_out/biometric_check_in_check_out_list.js",
	"Biometric Lunch Break": "biometric_integration/doctype/biometric_lunch_break/biometric_lunch_break_list.js",
	"Biometric Tea Break": "biometric_integration/doctype/biometric_tea_break/biometric_tea_break_list.js",
}

override_whitelisted_methods = {
	"frappe.desk.desktop.get_desktop_page": "biometric_integration.desk.workspace.get_desktop_page",
}
