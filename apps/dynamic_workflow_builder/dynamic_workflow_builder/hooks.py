app_name = "dynamic_workflow_builder"
app_title = "Dynamic Workflow Builder"
app_publisher = "Tejas"
app_description = "Smart approval engine with dynamic rules, visual workflow builder, SLA and escalation"
app_email = "hello@tejas.com"
app_license = "mit"

required_apps = ["frappe", "erpnext"]

app_include_js = "/assets/dynamic_workflow_builder/js/approval_actions.js"

doc_events = {
	"*": {
		"after_insert": "dynamic_workflow_builder.engine.processor.handle_document_event",
		"on_update": "dynamic_workflow_builder.engine.processor.handle_document_event",
		"on_submit": "dynamic_workflow_builder.engine.processor.handle_document_event",
		"on_update_after_submit": "dynamic_workflow_builder.engine.processor.handle_document_event",
	}
}

scheduler_events = {
	"hourly": [
		"dynamic_workflow_builder.engine.escalation.run_escalation_check",
	],
}

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["Approval Manager", "Approver", "Approval Employee"]]],
	},
]

doctype_js = {
	"DWB Approval Rule": "public/js/dwb_approval_rule.js",
}
