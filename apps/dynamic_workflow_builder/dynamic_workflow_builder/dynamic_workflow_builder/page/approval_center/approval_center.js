frappe.provide("dynamic_workflow_builder");

frappe.pages["approval-center"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Approval Center"),
		single_column: true,
	});

	wrapper.approval_center = new dynamic_workflow_builder.ApprovalCenter(wrapper);
	frappe.breadcrumbs.add("Dynamic Workflow Builder");
};

dynamic_workflow_builder.ApprovalCenter = class ApprovalCenter {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.setup();
	}

	setup() {
		this.page.main.html(`
			<div id="dwb-stats" class="row" style="margin-bottom:16px"></div>
			<div class="frappe-list" id="dwb-pending-list"></div>
		`);
		this.load();
		this.page.set_primary_action(__("Refresh"), () => this.load(), "refresh");
	}

	load() {
		frappe.call({
			method: "dynamic_workflow_builder.api.dashboard.get_dashboard_stats",
			callback: (r) => this.render_stats(r.message || {}),
		});
		frappe.call({
			method: "dynamic_workflow_builder.api.dashboard.get_my_pending",
			callback: (r) => this.render_pending(r.message || []),
		});
	}

	render_stats(stats) {
		const cards = [
			{ label: __("Pending Approvals"), value: stats.pending, color: "#2563eb" },
			{ label: __("Approved Today"), value: stats.approved_today, color: "#16a34a" },
			{ label: __("Rejected Today"), value: stats.rejected_today, color: "#dc2626" },
			{ label: __("Escalated"), value: stats.escalated, color: "#ea580c" },
			{ label: __("Overdue"), value: stats.overdue, color: "#7c3aed" },
		];
		this.page.main.find("#dwb-stats").html(
			cards
				.map(
					(c) => `
				<div class="col-sm-6 col-md-4 col-lg-2" style="margin-bottom:12px">
					<div style="border:1px solid var(--border-color);border-radius:10px;padding:14px;border-left:4px solid ${c.color}">
						<div style="font-size:12px;color:var(--text-muted)">${c.label}</div>
						<div style="font-size:24px;font-weight:700">${c.value || 0}</div>
					</div>
				</div>`
				)
				.join("")
		);
	}

	sla_color(status) {
		if (status === "Breached") return "#dc2626";
		if (status === "Near Breach") return "#ea580c";
		return "#16a34a";
	}

	render_pending(rows) {
		if (!rows.length) {
			this.page.main.find("#dwb-pending-list").html(`<p class="text-muted">${__("No pending approvals.")}</p>`);
			return;
		}
		const html = `
			<table class="table table-bordered">
				<thead><tr>
					<th>${__("Document")}</th>
					<th>${__("Level")}</th>
					<th>${__("Due")}</th>
					<th>${__("SLA")}</th>
					<th></th>
				</tr></thead>
				<tbody>
					${rows
						.map(
							(r) => `
						<tr>
							<td><a href="/app/${frappe.router.slug(r.reference_doctype)}/${r.reference_name}">${r.reference_doctype} ${r.reference_name}</a></td>
							<td>${r.current_level}</td>
							<td>${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}</td>
							<td><span style="color:${this.sla_color(r.sla_status)};font-weight:600">${r.sla_status}</span></td>
							<td>
								<button class="btn btn-xs btn-primary dwb-approve" data-name="${r.name}">${__("Approve")}</button>
								<button class="btn btn-xs btn-danger dwb-reject" data-name="${r.name}">${__("Reject")}</button>
							</td>
						</tr>`
						)
						.join("")}
				</tbody>
			</table>`;
		this.page.main.find("#dwb-pending-list").html(html);
		this.page.main.find(".dwb-approve").on("click", (e) => {
			dynamic_workflow_builder.act(e.target.dataset.name, "approve");
			setTimeout(() => this.load(), 800);
		});
		this.page.main.find(".dwb-reject").on("click", (e) => {
			dynamic_workflow_builder.act(e.target.dataset.name, "reject");
			setTimeout(() => this.load(), 800);
		});
	}
};
