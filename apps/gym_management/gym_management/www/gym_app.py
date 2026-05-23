# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.site_name = frappe.local.site
	context.app_title = "Gym Management"
	frappe.db.commit()  # nosemgrep
