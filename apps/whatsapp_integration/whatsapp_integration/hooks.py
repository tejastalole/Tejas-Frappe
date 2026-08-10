app_name = "whatsapp_integration"
app_title = "WhatsApp Integration"
app_publisher = "Tejas"
app_description = "WhatsApp Cloud API integration for Frappe / ERPNext"
app_email = "hello@tejas.com"
app_license = "mit"
app_version = "0.0.1"

required_apps = []

after_install = "whatsapp_integration.install.after_install"

# Desk includes
# app_include_css = "/assets/whatsapp_integration/css/whatsapp_integration.css"
# app_include_js = "/assets/whatsapp_integration/js/whatsapp_integration.js"

# Document Events
# ---------------
# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------
# scheduler_events = {
# 	"all": [
# 		"whatsapp_integration.tasks.all"
# 	],
# }

# Testing
# -------
# before_tests = "whatsapp_integration.install.before_tests"

# Overriding Methods
# ------------------------------
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "whatsapp_integration.event.get_events"
# }
