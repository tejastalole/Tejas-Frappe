app_name = "currencyinfo"
app_title = "Currency Info"
app_publisher = "Tejas"
app_description = "Real-time crypto trade stream from Binance WebSocket"
app_email = "tejas@example.com"
app_license = "mit"
app_version = "0.0.1"

after_install = "currencyinfo.install.after_install"
after_migrate = "currencyinfo.install.after_migrate"

app_include_css = [
	"/assets/currencyinfo/css/currencyinfo.css",
]

# Background streamer watchdog (keeps Binance WS loop alive)
scheduler_events = {
	"cron": {
		"*/1 * * * *": [
			"currencyinfo.currency_info.stream.scheduled_watchdog",
		]
	}
}
