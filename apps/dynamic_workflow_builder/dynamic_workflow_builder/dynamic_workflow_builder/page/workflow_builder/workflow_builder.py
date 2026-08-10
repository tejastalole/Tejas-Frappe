# Copyright (c) 2026, Tejas and contributors
# MIT License

import frappe


@frappe.whitelist()
def get_rule_for_builder(rule_name):
	frappe.only_for(("Approval Manager", "System Manager"))
	rule = frappe.get_doc("DWB Approval Rule", rule_name)
	return {
		"name": rule.name,
		"rule_name": rule.rule_name,
		"document_type": rule.document_type,
		"conditions": [
			{"field_name": c.field_name, "operator": c.operator, "value": c.value} for c in rule.conditions
		],
		"levels": [
			{
				"level": c.level,
				"approver_type": c.approver_type,
				"user": c.user,
				"role": c.role,
				"sla_hours": c.sla_hours,
			}
			for c in rule.levels
		],
		"workflow_graph": rule.workflow_graph,
	}
