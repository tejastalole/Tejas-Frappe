# Copyright (c) 2026, Tejas and contributors
# For license information, please see license.txt

"""Frappe page_renderer for ZKTeco ADMS /iclock/* paths."""

from __future__ import annotations

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response


class ZKTecoADMSRenderer(BaseRenderer):
	"""Intercepts /iclock/* before template lookup (works without Nginx rewrites)."""

	def can_render(self):
		# BaseRenderer strips leading slash: /iclock/cdata → iclock/cdata
		return self.path.startswith("iclock")

	def render(self):
		from zkteco_integration.api import handle_request

		try:
			frappe.set_user("Administrator")
			response = handle_request(frappe.local.request, self.path)
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title="ZKTeco ADMS Renderer Error", message=frappe.get_traceback())
			return Response("ERROR", status=500, mimetype="text/plain")
		else:
			frappe.db.commit()
			return response
