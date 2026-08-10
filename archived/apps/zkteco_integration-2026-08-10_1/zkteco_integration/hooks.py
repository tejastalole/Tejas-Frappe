app_name = "zkteco_integration"
app_title = "Exacuer Biometric"
app_publisher = "Exacuer"
app_description = "ZKTeco biometric attendance integration for ERPNext (local agent → cloud API)"
app_email = "support@exacuer.com"
app_license = "mit"
app_version = "1.0.0"

required_apps = ["hrms"]

after_install = "zkteco_integration.install.after_install"

# Cloud must NEVER dial LAN device IPs. Sync is via local agent HTTPS APIs.
# Optional: no page_renderer for ADMS in this architecture.

scheduler_events = {
	"hourly": [
		"zkteco_integration.tasks.mark_stale_devices_offline",
	],
}
