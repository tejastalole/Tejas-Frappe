frappe.provide("frappe_flow");

frappe.pages["automation-center"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Automation Center"), single_column: true });
	wrapper.automation_center = new frappe_flow.AutomationCenter(wrapper);
	frappe.breadcrumbs.add("Frappe Flow");
};

frappe_flow.AutomationCenter = class AutomationCenter {
	constructor(wrapper) {
		this.page = wrapper.page;
		this.setup();
	}

	setup() {
		this.page.main.html(`
			<div id="ff-stats" class="row" style="margin-bottom:16px"></div>
			<div class="row">
				<div class="col-md-6"><h5>${__("Recent Executions")}</h5><div id="ff-recent"></div></div>
				<div class="col-md-6"><h5>${__("Template Marketplace")}</h5><div id="ff-templates"></div></div>
			</div>
		`);
		this.page.set_primary_action(__("Refresh"), () => this.load(), "refresh");
		this.load();
	}

	load() {
		frappe.call({
			method: "frappe_flow.api.flow.get_dashboard_stats",
			callback: (r) => this.render_stats(r.message || {}),
		});
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "FF Flow Execution",
				fields: ["name", "flow", "status", "triggered_on", "execution_time", "reference_doctype", "reference_name"],
				order_by: "triggered_on desc",
				limit_page_length: 10,
			},
			callback: (r) => this.render_recent(r.message || []),
		});
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "FF Flow Template",
				fields: ["name", "template_name", "category", "description"],
				filters: { is_published: 1 },
				limit_page_length: 20,
			},
			callback: (r) => this.render_templates(r.message || []),
		});
	}

	render_stats(s) {
		const cards = [
			{ label: __("Active Flows"), value: s.active_flows, color: "#16a34a" },
			{ label: __("Failed Flows"), value: s.failed_flows, color: "#dc2626" },
			{ label: __("Success Rate %"), value: s.success_rate, color: "#2563eb" },
			{ label: __("Executions"), value: s.execution_count, color: "#7c3aed" },
		];
		this.page.main.find("#ff-stats").html(
			cards.map((c) => `
				<div class="col-sm-6 col-md-3" style="margin-bottom:12px">
					<div style="border:1px solid var(--border-color);border-radius:10px;padding:14px;border-left:4px solid ${c.color}">
						<div style="font-size:12px;color:var(--text-muted)">${c.label}</div>
						<div style="font-size:24px;font-weight:700">${c.value ?? 0}</div>
					</div>
				</div>`).join("")
		);
	}

	render_recent(rows) {
		if (!rows.length) {
			this.page.main.find("#ff-recent").html(`<p class="text-muted">${__("No executions yet.")}</p>`);
			return;
		}
		this.page.main.find("#ff-recent").html(`
			<table class="table table-bordered table-sm">
				<thead><tr><th>${__("Flow")}</th><th>${__("Status")}</th><th>${__("Time")}</th><th>${__("Duration")}</th></tr></thead>
				<tbody>${rows.map((r) => `
					<tr>
						<td><a href="/app/ff-flow-execution/${r.name}">${r.flow}</a></td>
						<td>${r.status}</td>
						<td>${r.triggered_on ? frappe.datetime.str_to_user(r.triggered_on) : ""}</td>
						<td>${r.execution_time || 0}s</td>
					</tr>`).join("")}
				</tbody>
			</table>`);
	}

	render_templates(rows) {
		if (!rows.length) {
			this.page.main.find("#ff-templates").html(`<p class="text-muted">${__("No templates published.")}</p>`);
			return;
		}
		this.page.main.find("#ff-templates").html(
			rows.map((t) => `
				<div style="border:1px solid var(--border-color);border-radius:8px;padding:12px;margin-bottom:8px">
					<strong>${frappe.utils.escape_html(t.template_name)}</strong>
					<span class="badge">${t.category}</span>
					<p class="text-muted" style="margin:6px 0 8px">${frappe.utils.escape_html(t.description || "")}</p>
					<button class="btn btn-xs btn-primary ff-install" data-name="${t.name}">${__("Install")}</button>
				</div>`).join("")
		);
		this.page.main.find(".ff-install").on("click", (e) => {
			frappe.call({
				method: "frappe_flow.api.flow.install_template",
				args: { template_name: e.target.dataset.name },
				callback(r) {
					frappe.show_alert({ message: r.message.message, indicator: "green" });
				},
			});
		});
	}
};
