frappe.provide("dynamic_workflow_builder");

frappe.pages["workflow-builder"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Workflow Builder"),
		single_column: true,
	});

	const rule_name = frappe.utils.get_query_params().rule || frappe.route_options?.rule_name;
	wrapper.workflow_builder = new dynamic_workflow_builder.WorkflowBuilder(wrapper, rule_name);
	frappe.breadcrumbs.add("Dynamic Workflow Builder");
};

dynamic_workflow_builder.WorkflowBuilder = class WorkflowBuilder {
	constructor(wrapper, rule_name) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.rule_name = rule_name;
		this.nodes = [];
		this.setup();
	}

	setup() {
		this.page.main.html(`
			<div class="sales-map-toolbar">
				<div id="dwb-rule-select"></div>
				<button class="btn btn-primary btn-sm" id="dwb-save-flow">${__("Save Workflow")}</button>
				<button class="btn btn-default btn-sm" id="dwb-auto-layout">${__("Auto Layout")}</button>
				<div class="dwb-flow-legend">
					<span class="start">${__("Start")}</span>
					<span class="condition">${__("Condition")}</span>
					<span class="approval">${__("Approval")}</span>
					<span class="end">${__("End")}</span>
				</div>
			</div>
			<div class="dwb-flow-canvas" id="dwb-flow-canvas">
				<svg class="dwb-flow-svg" id="dwb-flow-svg"></svg>
			</div>
		`);

		this.rule_field = frappe.ui.form.make_control({
			parent: this.page.main.find("#dwb-rule-select"),
			df: {
				fieldtype: "Link",
				label: __("Approval Rule"),
				options: "DWB Approval Rule",
				fieldname: "rule_name",
				change: () => {
					this.rule_name = this.rule_field.get_value();
					this.load_rule();
				},
			},
			render_input: true,
		});

		if (this.rule_name) this.rule_field.set_value(this.rule_name);

		this.canvas = this.page.main.find("#dwb-flow-canvas")[0];
		this.svg = this.page.main.find("#dwb-flow-svg")[0];

		this.page.main.find("#dwb-save-flow").on("click", () => this.save());
		this.page.main.find("#dwb-auto-layout").on("click", () => this.auto_layout());

		this.enable_drag();
		this.load_rule();
	}

	load_rule() {
		if (!this.rule_name) return;
		frappe.call({
			method: "dynamic_workflow_builder.dynamic_workflow_builder.page.workflow_builder.workflow_builder.get_rule_for_builder",
			args: { rule_name: this.rule_name },
			callback: (r) => {
				const data = r.message;
				let graph = data.workflow_graph;
				if (typeof graph === "string") {
					try {
						graph = JSON.parse(graph);
					} catch (e) {
						graph = null;
					}
				}
				if (graph && graph.nodes) {
					this.nodes = graph.nodes;
				} else {
					this.build_from_rule(data);
				}
				this.render();
			},
		});
	}

	build_from_rule(data) {
		this.nodes = [{ id: "start", type: "start", label: __("START"), x: 40, y: 80 }];
		let y = 180;
		(data.conditions || []).forEach((cond, idx) => {
			this.nodes.push({
				id: `cond-${idx}`,
				type: "condition",
				label: `${cond.field_name} ${cond.operator} ${cond.value}`,
				x: 40,
				y,
			});
			y += 100;
		});
		(data.levels || []).forEach((level) => {
			this.nodes.push({
				id: `level-${level.level}`,
				type: "approval",
				label: `${__("Level")} ${level.level}: ${level.approver_type}`,
				x: 40,
				y,
			});
			y += 100;
		});
		this.nodes.push({ id: "end", type: "end", label: __("APPROVED"), x: 40, y });
	}

	auto_layout() {
		let y = 60;
		this.nodes.forEach((node, idx) => {
			node.x = 80;
			node.y = y;
			y += 110;
		});
		this.render();
	}

	render() {
		this.canvas.querySelectorAll(".dwb-flow-node").forEach((el) => el.remove());
		this.nodes.forEach((node) => {
			const el = document.createElement("div");
			el.className = `dwb-flow-node ${node.type}`;
			el.dataset.id = node.id;
			el.style.left = `${node.x}px`;
			el.style.top = `${node.y}px`;
			el.innerHTML = `<div class="dwb-flow-node__title">${node.type}</div><div class="dwb-flow-node__body">${frappe.utils.escape_html(node.label)}</div>`;
			this.canvas.appendChild(el);
		});
		this.draw_edges();
	}

	draw_edges() {
		const svg = this.svg;
		svg.innerHTML = "";
		for (let i = 0; i < this.nodes.length - 1; i += 1) {
			const a = this.nodes[i];
			const b = this.nodes[i + 1];
			const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
			const x1 = a.x + 90;
			const y1 = a.y + 70;
			const x2 = b.x + 90;
			const y2 = b.y;
			line.setAttribute("d", `M ${x1} ${y1} C ${x1} ${y1 + 40}, ${x2} ${y2 - 40}, ${x2} ${y2}`);
			line.setAttribute("stroke", "#94a3b8");
			line.setAttribute("stroke-width", "2");
			line.setAttribute("fill", "none");
			line.setAttribute("marker-end", "url(#arrow)");
			svg.appendChild(line);
		}
		const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
		const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
		marker.setAttribute("id", "arrow");
		marker.setAttribute("markerWidth", "8");
		marker.setAttribute("markerHeight", "8");
		marker.setAttribute("refX", "6");
		marker.setAttribute("refY", "3");
		marker.setAttribute("orient", "auto");
		const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
		poly.setAttribute("points", "0 0, 8 3, 0 6");
		poly.setAttribute("fill", "#94a3b8");
		marker.appendChild(poly);
		defs.appendChild(marker);
		svg.appendChild(defs);
	}

	enable_drag() {
		let active = null;
		let offsetX = 0;
		let offsetY = 0;

		this.canvas.addEventListener("mousedown", (e) => {
			const nodeEl = e.target.closest(".dwb-flow-node");
			if (!nodeEl) return;
			active = this.nodes.find((n) => n.id === nodeEl.dataset.id);
			offsetX = e.clientX - nodeEl.offsetLeft;
			offsetY = e.clientY - nodeEl.offsetTop;
		});

		document.addEventListener("mousemove", (e) => {
			if (!active) return;
			const rect = this.canvas.getBoundingClientRect();
			active.x = e.clientX - rect.left - offsetX + this.canvas.scrollLeft;
			active.y = e.clientY - rect.top - offsetY + this.canvas.scrollTop;
			const el = this.canvas.querySelector(`[data-id="${active.id}"]`);
			if (el) {
				el.style.left = `${active.x}px`;
				el.style.top = `${active.y}px`;
			}
			this.draw_edges();
		});

		document.addEventListener("mouseup", () => {
			active = null;
		});
	}

	save() {
		if (!this.rule_name) {
			frappe.msgprint(__("Select an Approval Rule first."));
			return;
		}
		const graph = { nodes: this.nodes, edges: this.nodes.slice(0, -1).map((n, i) => ({ from: n.id, to: this.nodes[i + 1].id })) };
		frappe.call({
			method: "dynamic_workflow_builder.api.dashboard.save_workflow_graph",
			args: { rule_name: this.rule_name, workflow_graph: graph },
			callback() {
				frappe.show_alert({ message: __("Workflow saved"), indicator: "green" });
			},
		});
	}
};
