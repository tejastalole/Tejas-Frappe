# Copyright (c) 2026, Tejas and contributors
# MIT License

import re

from frappe.utils import flt

from ai_bot.utils.doctype_discovery import get_config

FIELD_ALIASES = {
	"grand total": "grand_total",
	"grandtotal": "grand_total",
	"total amount": "grand_total",
	"total": "grand_total",
	"amount": "grand_total",
	"net total": "net_total",
	"qty": "qty",
	"quantity": "qty",
}


def parse_field_filters(message: str, doctype: str) -> dict:
	"""Parse field conditions like 'grand total is 5000' or 'total above 10000'."""
	filters = {}
	message = message.lower()
	config = get_config(doctype)
	amount_field = config.get("amount_field")

	if amount_field:
		lakh_m = re.search(r"\b([\d,.]+)\s*(?:lakh|lac|lakhs)\b", message, re.I)
		if lakh_m:
			filters[amount_field] = [">", flt(lakh_m.group(1).replace(",", "")) * 100000]
			return filters
		crore_m = re.search(r"\b([\d,.]+)\s*(?:crore|cr)\b", message, re.I)
		if crore_m:
			filters[amount_field] = [">", flt(crore_m.group(1).replace(",", "")) * 10000000]
			return filters

		match = re.search(
			r"\b(?:above|over|greater than|more than)\s+([\d,.]+)\b",
			message,
			re.I,
		)
		if match:
			filters[amount_field] = [">", flt(match.group(1).replace(",", ""))]
			return filters
		match = re.search(r"\b(?:below|under|less than)\s+([\d,.]+)\b", message, re.I)
		if match:
			filters[amount_field] = ["<", flt(match.group(1).replace(",", ""))]
			return filters

	for label, fieldname in sorted(FIELD_ALIASES.items(), key=lambda x: -len(x[0])):
		if fieldname == "grand_total" and not config.get("amount_field"):
			continue

		escaped = re.escape(label)

		# equals: is 5000, = 5000, equals 5000
		match = re.search(
			rf"{escaped}\s*(?:is|=|equals?|equal to)\s*([\d,.]+)",
			message,
			re.I,
		)
		if match:
			filters[fieldname] = flt(match.group(1).replace(",", ""))
			return filters

		# greater than
		match = re.search(
			rf"{escaped}\s*(?:>|greater than|more than|above|over)\s*([\d,.]+)",
			message,
			re.I,
		)
		if match:
			filters[fieldname] = [">", flt(match.group(1).replace(",", ""))]
			return filters

		# less than
		match = re.search(
			rf"{escaped}\s*(?:<|less than|below|under)\s*([\d,.]+)",
			message,
			re.I,
		)
		if match:
			filters[fieldname] = ["<", flt(match.group(1).replace(",", ""))]
			return filters

	return filters
