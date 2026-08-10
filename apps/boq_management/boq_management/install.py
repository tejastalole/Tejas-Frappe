# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


CATEGORIES = [
	"Metal Roofing",
	"Insulated Metal Roofing",
	"Structural Purlins",
	"Structural Decking",
	"Fire Protection Systems",
	"Metal False Ceiling",
	"Façade Systems",
	"Louvers",
	"Add-On Roofs",
]

SUB_CATEGORIES = [
	"Roof Sheet",
	"Panel",
	"Flashing",
	"Accessories",
	"Fasteners",
	"Sealant",
	"Labour",
	"Structural Member",
	"Decking",
	"Ceiling Grid",
	"Façade Panel",
	"Frame",
	"Fire Protection",
	"Testing",
]

# category -> list of (sub_category, item_type, items[(name, spec, uom)])
SEED_DATA = {
	"Metal Roofing": [
		("Roof Sheet", "Material", [
			("Roof Sheet 0.5 mm TCT", "0.5 mm TCT", "Sqm"),
			("Roof Sheet 0.6 mm TCT", "0.6 mm TCT", "Sqm"),
		]),
		("Flashing", "Material", [
			("Ridge Flashing", "", "Meter"),
			("Side Flashing", "", "Meter"),
			("Eave Flashing", "", "Meter"),
		]),
		("Accessories", "Accessories", [
			("Gutter", "", "Meter"),
			("Down Take Pipe", "", "Meter"),
			("Turbo Ventilator", "", "Nos"),
			("Skylight Sheet", "", "Sqm"),
			("Polycarbonate Sheet", "", "Sqm"),
		]),
		("Fasteners", "Fasteners", [
			("Self Drilling Screw", "", "Nos"),
			("EPDM Washer", "", "Nos"),
		]),
		("Sealant", "Material", [
			("Sealant", "", "Nos"),
			("Foam Filler", "", "Nos"),
		]),
		("Labour", "Labour", [
			("Installation Labour", "Roof installation", "Sqm"),
		]),
	],
	"Insulated Metal Roofing": [
		("Panel", "Material", [
			("PUF Sandwich Panel", "", "Sqm"),
			("PIR Panel", "", "Sqm"),
			("Roof Panel", "", "Sqm"),
			("Wall Panel", "", "Sqm"),
		]),
		("Flashing", "Material", [("Corner Flashing", "", "Meter")]),
		("Sealant", "Material", [("Sealant", "", "Nos")]),
		("Fasteners", "Fasteners", [("Fasteners", "", "Nos")]),
		("Accessories", "Accessories", [("Accessories", "", "Nos")]),
		("Labour", "Labour", [("Installation", "", "Sqm")]),
	],
	"Structural Purlins": [
		("Structural Member", "Material", [
			("Z Purlin 150", "", "Kg"),
			("Z Purlin 200", "", "Kg"),
			("C Purlin", "", "Kg"),
		]),
		("Accessories", "Accessories", [
			("Cleat", "", "Nos"),
			("Sag Rod", "", "Nos"),
			("Base Plate", "", "Nos"),
		]),
		("Fasteners", "Fasteners", [
			("Nut Bolt", "", "Nos"),
			("Anchor Fastener", "", "Nos"),
		]),
		("Labour", "Labour", [
			("Painting", "", "Sqm"),
			("Erection Labour", "", "Kg"),
		]),
	],
	"Structural Decking": [
		("Decking", "Material", [
			("Deck Sheet", "", "Sqm"),
			("Shear Stud", "", "Nos"),
			("Edge Trim", "", "Meter"),
			("Pour Stop", "", "Meter"),
		]),
		("Fasteners", "Fasteners", [("Fixing Screw", "", "Nos")]),
		("Labour", "Labour", [("Installation", "", "Sqm")]),
	],
	"Metal False Ceiling": [
		("Ceiling Grid", "Material", [
			("Metal Ceiling Panel", "", "Sqm"),
			("T Grid", "", "Sqm"),
			("Suspension Rod", "", "Nos"),
			("Hanger", "", "Nos"),
			("Main Runner", "", "Meter"),
			("Cross Tee", "", "Meter"),
			("Perimeter Trim", "", "Meter"),
			("Access Panel", "", "Nos"),
		]),
		("Labour", "Labour", [("Installation", "", "Sqm")]),
	],
	"Façade Systems": [
		("Façade Panel", "Material", [
			("ACP Panel", "", "Sqm"),
			("Glass", "", "Sqm"),
		]),
		("Frame", "Material", [
			("Aluminium Frame", "", "Meter"),
			("Bracket", "", "Nos"),
		]),
		("Sealant", "Material", [("Silicone", "", "Nos")]),
		("Fasteners", "Fasteners", [
			("Anchor Bolt", "", "Nos"),
			("Fasteners", "", "Nos"),
		]),
		("Labour", "Labour", [("Installation", "", "Sqm")]),
	],
	"Louvers": [
		("Façade Panel", "Material", [
			("Aluminium Louvers", "", "Sqm"),
			("Steel Louvers", "", "Sqm"),
		]),
		("Frame", "Material", [("Frame", "", "Meter"), ("Bracket", "", "Nos")]),
		("Fasteners", "Fasteners", [
			("Anchor Bolt", "", "Nos"),
			("Fasteners", "", "Nos"),
		]),
		("Labour", "Labour", [("Installation", "", "Sqm")]),
	],
	"Fire Protection Systems": [
		("Fire Protection", "Material", [
			("Fire Curtain", "", "Sqm"),
			("Fire Board", "", "Sqm"),
			("Fire Sealant", "", "Nos"),
			("Fire Stop Collar", "", "Nos"),
		]),
		("Accessories", "Accessories", [
			("Anchor", "", "Nos"),
			("Support", "", "Nos"),
		]),
		("Labour", "Labour", [
			("Installation", "", "Sqm"),
			("Testing", "", "Nos"),
		]),
	],
	"Add-On Roofs": [
		("Roof Sheet", "Material", [("Add-On Roof Sheet", "", "Sqm")]),
		("Flashing", "Material", [("Add-On Flashing", "", "Meter")]),
		("Fasteners", "Fasteners", [("Self Drilling Screw", "", "Nos")]),
		("Labour", "Labour", [("Installation Labour", "", "Sqm")]),
	],
}


def after_install():
	_seed_roles()
	_seed_uoms()
	_seed_settings()
	_seed_masters()
	_sync_workspace()
	frappe.db.commit()


def _seed_uoms():
	"""Create BOQ-specific UOMs: m2, Set, LS."""
	uoms = [
		{"uom_name": "m2", "name": "m2", "must_be_whole_number": 0},
		{"uom_name": "Set", "name": "Set", "must_be_whole_number": 1},
		{"uom_name": "LS", "name": "LS", "must_be_whole_number": 1},
	]
	for row in uoms:
		if frappe.db.exists("UOM", row["name"]):
			continue
		frappe.get_doc({"doctype": "UOM", **row, "enabled": 1}).insert(ignore_permissions=True)


def _seed_roles():
	for role in ("BOQ Manager", "BOQ User"):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def _seed_settings():
	if frappe.db.exists("BOQ Settings", "BOQ Settings"):
		doc = frappe.get_doc("BOQ Settings", "BOQ Settings")
		if not doc.default_final_rate_uom and frappe.db.exists("UOM", "m2"):
			doc.default_final_rate_uom = "m2"
			doc.default_overhead_percent = doc.default_overhead_percent or 10
			doc.default_contractor_profit_percent = doc.default_contractor_profit_percent or 15
			doc.save(ignore_permissions=True)
		return
	frappe.get_doc(
		{
			"doctype": "BOQ Settings",
			"enable_project_mandatory": 1,
			"default_overhead_percent": 10,
			"default_contractor_profit_percent": 15,
			"default_final_rate_uom": "m2" if frappe.db.exists("UOM", "m2") else None,
		}
	).insert(ignore_permissions=True)


def _seed_masters():
	sub_map = {}
	for idx, cat_name in enumerate(CATEGORIES, start=1):
		if not frappe.db.exists("BOQ Category", cat_name):
			frappe.get_doc(
				{"doctype": "BOQ Category", "category_name": cat_name, "sort_order": idx, "is_active": 1}
			).insert(ignore_permissions=True)

		for sub_name, item_type, items in SEED_DATA.get(cat_name, []):
			sub_key = f"{cat_name}::{sub_name}"
			if sub_key not in sub_map:
				existing = frappe.db.get_value(
					"BOQ Sub Category",
					{"boq_category": cat_name, "sub_category_name": sub_name},
					"name",
				)
				if existing:
					sub_map[sub_key] = existing
				else:
					doc = frappe.get_doc(
						{
							"doctype": "BOQ Sub Category",
							"sub_category_name": sub_name,
							"boq_category": cat_name,
							"item_type": item_type,
							"is_active": 1,
						}
					)
					doc.insert(ignore_permissions=True)
					sub_map[sub_key] = doc.name

			sub_category = sub_map[sub_key]
			for item_name, spec, uom in items:
				if frappe.db.exists(
					"BOQ Item Master",
					{"boq_category": cat_name, "item_name": item_name},
				):
					continue
				frappe.get_doc(
					{
						"doctype": "BOQ Item Master",
						"item_name": item_name,
						"boq_category": cat_name,
						"boq_sub_category": sub_category,
						"specification": spec,
						"default_uom": _resolve_uom(uom),
						"is_active": 1,
					}
				).insert(ignore_permissions=True)


def _resolve_uom(uom: str) -> str:
	aliases = {
		"Sqm": "m2",
		"Square Meter": "m2",
		"m²": "m2",
		"Meter": "Meter",
		"Nos": "Nos",
		"Kg": "Kg",
		"Lump Sum": "LS",
	}
	resolved = aliases.get(uom, uom)
	if frappe.db.exists("UOM", resolved):
		return resolved
	if frappe.db.exists("UOM", uom):
		return uom
	_seed_uoms()
	if frappe.db.exists("UOM", resolved):
		return resolved
	return uom


def _sync_workspace():
	import os

	from frappe.modules.import_file import import_file_by_path

	path = frappe.get_app_path(
		"boq_management", "boq_management", "workspace", "boq_management", "boq_management.json"
	)
	if os.path.exists(path):
		import_file_by_path(path, force=True, ignore_version=True)
