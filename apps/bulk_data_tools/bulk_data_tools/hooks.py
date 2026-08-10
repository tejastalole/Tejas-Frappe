app_name = "bulk_data_tools"
app_title = "Bulk Data Tools"
app_publisher = "Tejas"
app_description = "Bulk delete and manage DocType records in Frappe / ERPNext"
app_email = "hello@tejas.com"
app_license = "mit"
app_version = "0.0.1"

required_apps = ["frappe"]

after_install = "bulk_data_tools.install.after_install"
