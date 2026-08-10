app_name = "biometric_integration"
app_title = "Biometric Integration"
app_publisher = "Tejas"
app_description = "ADMS / ZKTeco biometric device integration for Frappe / ERPNext"
app_email = "hello@tejas.com"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["erpnext"]

after_install = "biometric_integration.install.after_install"

# ADMS /iclock is handled by zkteco_integration (page_renderer).
# Keep this app for TCP pull / device masters only while both are installed.
# page_renderer = [
# 	"biometric_integration.renderers.ZKTecoADMSRenderer",
# ]

scheduler_events = {
	"cron": {
		"*/10 * * * *": [
			"biometric_integration.scheduler.pull_attendance"
		]
	}
}
