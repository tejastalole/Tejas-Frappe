app_name = "boq_management"
app_title = "BOQ Management"
app_publisher = "Tejas"
app_description = "Project-based Bill of Quantities for EPC roofing and façade contracting"
app_email = "hello@tejas.com"
app_license = "mit"

required_apps = ["frappe", "erpnext"]

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["BOQ Manager", "BOQ User"]]],
	},
]

doctype_js = {
	"BOQ": "public/js/boq.js",
	"BOQ Item Master": "public/js/boq_item_master.js",
}

app_include_css = "/assets/boq_management/css/boq.css"

after_install = "boq_management.install.after_install"
