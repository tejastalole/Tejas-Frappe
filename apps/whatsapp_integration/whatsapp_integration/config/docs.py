from frappe import _


def get_data():
	return [
		{
			"label": _("WhatsApp"),
			"items": [
				{
					"type": "doctype",
					"name": "WhatsApp Settings",
					"label": _("WhatsApp Settings"),
					"description": _("Meta Cloud API credentials"),
				},
				{
					"type": "doctype",
					"name": "WhatsApp Message",
					"label": _("WhatsApp Message"),
					"description": _("Sent and received messages"),
				},
			],
		}
	]
