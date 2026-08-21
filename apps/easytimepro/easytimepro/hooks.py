app_name = "easytimepro"
app_title = "Easy TimePro"
app_publisher = "Tejas"
app_description = "Fetch biometric punches from ZKTeco Easy TimePro into Frappe"
app_email = "tejas@example.com"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["erpnext"]

after_install = "easytimepro.install.after_install"
after_migrate = "easytimepro.install.after_migrate"

doctype_js = {
	"Easy TimePro Settings": "easy_timepro/doctype/easy_timepro_settings/easy_timepro_settings.js",
}

doctype_list_js = {
	"Easy TimePro Punch Log": "easy_timepro/doctype/easy_timepro_punch_log/easy_timepro_punch_log_list.js",
	"Employee Checkin": "public/js/employee_checkin_list.js",
}

app_include_css = [
	"/assets/easytimepro/css/easytimepro_workspace.css",
]

app_include_js = [
	"/assets/easytimepro/js/workspace_glass.js",
]

scheduler_events = {
	"cron": {
		# Watchdog only — real polling uses Sync Interval (Seconds) via background jobs
		"*/1 * * * *": [
			"easytimepro.easy_timepro.sync.scheduled_sync",
		]
	}
}
