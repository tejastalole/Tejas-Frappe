app_name = "biometric_integration"
app_title = "Biometric Integration"
app_publisher = "Tejas"
app_description = "ADMS / ZKTeco biometric device integration for Frappe / ERPNext"
app_email = "hello@tejas.com"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["erpnext"]

after_install = "biometric_integration.install.after_install"

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

override_whitelisted_methods = {
	"frappe.desk.desktop.get_desktop_page": "biometric_integration.desk.workspace.get_desktop_page",
}
