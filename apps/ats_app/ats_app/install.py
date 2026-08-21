# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


def after_install():
	ensure_workspace()


def after_migrate():
	ensure_workspace()


def ensure_workspace():
	if frappe.db.exists("Workspace", "ATS"):
		ws = frappe.get_doc("Workspace", "ATS")
	else:
		ws = frappe.new_doc("Workspace")
		ws.name = "ATS"
		ws.label = "ATS"
		ws.title = "ATS"

	ws.module = "ATS"
	ws.public = 1
	ws.is_hidden = 0
	ws.icon = "users"
	ws.content = (
		'[{"id":"hdr","type":"header","data":{"text":"<span class=\\"h4\\"><b>ATS</b></span>","col":12}},'
		'{"id":"sc1","type":"shortcut","data":{"shortcut_name":"Job Descriptions","col":4}},'
		'{"id":"sc2","type":"shortcut","data":{"shortcut_name":"Check Resume Score","col":4}},'
		'{"id":"card","type":"card","data":{"card_name":"ATS","col":6}}]'
	)
	ws.set("shortcuts", [])
	ws.append(
		"shortcuts",
		{
			"label": "Job Descriptions",
			"link_to": "Job Description",
			"type": "DocType",
			"doc_view": "List",
			"color": "Blue",
		},
	)
	ws.append(
		"shortcuts",
		{
			"label": "Check Resume Score",
			"link_to": "ATS Resume Check",
			"type": "DocType",
			"doc_view": "List",
			"color": "Green",
		},
	)
	ws.set("links", [])
	ws.append("links", {"type": "Card Break", "label": "ATS", "link_count": 2})
	ws.append(
		"links",
		{
			"type": "Link",
			"label": "Job Description",
			"link_type": "DocType",
			"link_to": "Job Description",
			"onboard": 1,
		},
	)
	ws.append(
		"links",
		{
			"type": "Link",
			"label": "ATS Resume Check",
			"link_type": "DocType",
			"link_to": "ATS Resume Check",
			"onboard": 1,
		},
	)

	if ws.is_new():
		ws.insert(ignore_permissions=True)
	else:
		ws.save(ignore_permissions=True)
