import json

import frappe
from frappe import DoesNotExistError
from frappe.desk.desktop import Workspace


@frappe.whitelist()
def get_desktop_page(page):
	"""Add record counts to Biometric Integration workspace card links."""
	try:
		page_data = json.loads(page) if isinstance(page, str) else page
		workspace = Workspace(page_data)
		workspace.build_workspace()
		result = {
			"charts": workspace.charts,
			"shortcuts": workspace.shortcuts,
			"cards": workspace.cards,
			"onboardings": workspace.onboardings,
			"quick_lists": workspace.quick_lists,
			"number_cards": workspace.number_cards,
			"custom_blocks": workspace.custom_blocks,
		}
	except DoesNotExistError:
		frappe.log_error("Workspace Missing")
		return {}

	if page_data.get("name") == "Biometric Integration":
		_enrich_card_link_counts(result)

	return result


def _enrich_card_link_counts(result):
	for card in result.get("cards", {}).get("items", []):
		for item in card.get("links", []):
			if item.get("link_type") != "DocType":
				continue

			doctype = item.get("link_to")
			if not doctype:
				continue

			meta = frappe.get_meta(doctype)
			if meta.issingle:
				continue

			item["record_count"] = frappe.db.count(doctype)
