# Copyright (c) 2026, Tejas and contributors
# MIT License

"""DocType aliases and query metadata for AI Bot skills."""

DOCTYPE_CONFIG = {
	"Sales Order": {
		"aliases": ["sales order", "sales orders", "so", "sale order", "sale orders"],
		"date_field": "transaction_date",
		"amount_field": "grand_total",
	},
	"Purchase Order": {
		"aliases": ["purchase order", "purchase orders", "po"],
		"date_field": "transaction_date",
		"amount_field": "grand_total",
	},
	"Sales Invoice": {
		"aliases": ["sales invoice", "sales invoices", "invoice", "invoices", "si"],
		"date_field": "posting_date",
		"amount_field": "grand_total",
	},
	"Purchase Invoice": {
		"aliases": ["purchase invoice", "purchase invoices", "pi"],
		"date_field": "posting_date",
		"amount_field": "grand_total",
	},
	"Quotation": {
		"aliases": ["quotation", "quotations", "quote", "quotes"],
		"date_field": "transaction_date",
		"amount_field": "grand_total",
	},
	"Customer": {
		"aliases": ["customer", "customers"],
		"date_field": "creation",
		"amount_field": None,
	},
	"Item": {
		"aliases": ["item", "items", "product", "products"],
		"date_field": "creation",
		"amount_field": None,
	},
	"Delivery Note": {
		"aliases": ["delivery note", "delivery notes", "dn"],
		"date_field": "posting_date",
		"amount_field": "grand_total",
	},
	"Work Order": {
		"aliases": ["work order", "work orders", "wo"],
		"date_field": "planned_start_date",
		"amount_field": None,
	},
	"Lead": {
		"aliases": ["lead", "leads"],
		"date_field": "creation",
		"amount_field": None,
	},
	"Opportunity": {
		"aliases": ["opportunity", "opportunities"],
		"date_field": "creation",
		"amount_field": "opportunity_amount",
	},
	"Leave Application": {
		"aliases": ["leave application", "leave applications", "leave"],
		"date_field": "from_date",
		"amount_field": None,
	},
	"Employee": {
		"aliases": ["employee", "employees", "staff"],
		"date_field": "creation",
		"amount_field": None,
	},
	"Material Request": {
		"aliases": ["material request", "material requests", "mr"],
		"date_field": "transaction_date",
		"amount_field": None,
	},
	"Expense Claim": {
		"aliases": ["expense claim", "expense claims"],
		"date_field": "posting_date",
		"amount_field": "total_claimed_amount",
	},
}

_ALIAS_TO_DOCTYPE = {}
for doctype, config in DOCTYPE_CONFIG.items():
	for alias in config["aliases"]:
		_ALIAS_TO_DOCTYPE[alias] = doctype


def resolve_doctype(phrase: str) -> str | None:
	phrase = phrase.strip().lower()
	if phrase in _ALIAS_TO_DOCTYPE:
		return _ALIAS_TO_DOCTYPE[phrase]
	for alias, doctype in sorted(_ALIAS_TO_DOCTYPE.items(), key=lambda x: -len(x[0])):
		if alias in phrase:
			return doctype
	return None


def get_config(doctype: str) -> dict:
	return DOCTYPE_CONFIG.get(doctype, {"date_field": "creation", "amount_field": None})


def list_supported_doctypes() -> list[str]:
	return list(DOCTYPE_CONFIG.keys())
