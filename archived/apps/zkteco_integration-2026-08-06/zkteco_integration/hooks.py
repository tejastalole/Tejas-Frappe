app_name = "zkteco_integration"
app_title = "ZKTeco Integration"
app_publisher = "Tejas"
app_description = "ADMS push integration for ZKTeco SenseFace devices"
app_email = "hello@tejas.com"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["hrms"]

# Intercept SenseFace / ZKTeco ADMS paths: /iclock/cdata, /iclock/getrequest, ...
page_renderer = [
	"zkteco_integration.renderers.ZKTecoADMSRenderer",
]
