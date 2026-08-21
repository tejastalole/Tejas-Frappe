# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe
from frappe.model.document import Document


class CurrencyInfoSettings(Document):
	def validate(self):
		if self.symbol:
			self.symbol = self.symbol.strip().upper()
		if self.stream_url:
			self.stream_url = self.stream_url.strip()

	def on_update(self):
		# Restart stream when settings change
		frappe.enqueue(
			"currencyinfo.currency_info.stream.ensure_stream_loop",
			queue="short",
			force=True,
			enqueue_after_commit=True,
		)
