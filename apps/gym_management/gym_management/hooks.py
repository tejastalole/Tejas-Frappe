app_name = "gym_management"
app_title = "Gym Management"
app_publisher = "Tejas"
app_description = "Manage gym members, plans, memberships, trainers, and attendance"
app_email = "hello@tejas.com"
app_license = "mit"

required_apps = ["frappe"]

app_include_js = "/assets/gym_management/js/gym_geo.js"

website_route_rules = [
	{"from_route": "/gym-app", "to_route": "gym_app"},
	{"from_route": "/gym-app/<path:app_path>", "to_route": "gym_app"},
]

add_to_apps_screen = [
	{
		"name": "gym_management",
		"logo": "/assets/gym_management/gym_pwa/icon.svg",
		"title": "Gym Management",
		"route": "/gym-app",
		"has_permission": "gym_management.api.mobile.has_app_permission",
	}
]

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["Gym Manager", "Gym User"]]],
	},
]

doctype_js = {
	"Gym Member": "public/js/gym_member.js",
	"Attendance Log": "public/js/attendance_log.js",
}
