app_name = "ats_app"
app_title = "ATS"
app_publisher = "Tejas"
app_description = "Simple ATS score checker for resumes vs job descriptions"
app_email = "tejas@example.com"
app_license = "mit"
app_version = "0.0.1"

after_install = "ats_app.install.after_install"
after_migrate = "ats_app.install.after_migrate"

doctype_js = {
	"ATS Resume Check": "ats/doctype/ats_resume_check/ats_resume_check.js",
}
