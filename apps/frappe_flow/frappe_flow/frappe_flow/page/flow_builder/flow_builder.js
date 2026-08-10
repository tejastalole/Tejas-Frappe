frappe.provide("frappe_flow");

frappe.pages["flow-builder"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Flow Builder"), single_column: true });
	const flow_name = frappe.utils.get_query_params().flow || frappe.route_options?.flow_name;
	wrapper.flow_builder = new frappe_flow.FlowBuilder(wrapper, flow_name);
	frappe.breadcrumbs.add("Frappe Flow");
};

frappe_flow.FlowBuilder = class FlowBuilder {
	constructor(wrapper, flow_name) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.flow_name = flow_name;
		this.nodes = [];
		this.edges = [];
		this.selected = null;
		this.connect_mode = false;
		this.connect_source = null;
		this.setup();
	}

	setup() {
		this.page.main.html(`
			<div class="ff-flow-toolbar">
				<div id="ff-flow-select"></div>
				<button class="btn btn-primary btn-sm" id="ff-save">${__("Save Flow")}</button>
				<button class="btn btn-default btn-sm" id="ff-auto">${__("Auto Layout")}</button>
				<button class="btn btn-default btn-sm" id="ff-connect">${__("Connect")}</button>
				<button class="btn btn-default btn-sm" id="ff-disconnect">${__("Remove Links")}</button>
			</div>
			<div class="ff-flow-hint text-muted small" id="ff-hint">
				${__("Tip: Select a block, click Connect, then click the next block. Or select a block and add a new one to insert in between.")}
			</div>
			<div class="ff-palette">
				<button class="btn btn-default btn-xs" data-type="condition">${__("Condition")}</button>
				<button class="btn btn-default btn-xs" data-type="send_email">${__("Email")}</button>
				<button class="btn btn-default btn-xs" data-type="send_whatsapp">${__("WhatsApp")}</button>
				<button class="btn btn-default btn-xs" data-type="create_task">${__("Task")}</button>
				<button class="btn btn-default btn-xs" data-type="assign_user">${__("Assign")}</button>
				<button class="btn btn-default btn-xs" data-type="webhook">${__("Webhook")}</button>
				<button class="btn btn-default btn-xs" data-type="delay">${__("Delay")}</button>
				<button class="btn btn-default btn-xs" data-type="approval">${__("Approval")}</button>
				<button class="btn btn-default btn-xs" data-type="ai">${__("AI")}</button>
			</div>
			<div class="ff-flow-canvas" id="ff-canvas"><svg class="ff-flow-svg" id="ff-svg"></svg></div>
		`);

		this.rule_field = frappe.ui.form.make_control({
			parent: this.page.main.find("#ff-flow-select"),
			df: {
				fieldtype: "Link",
				options: "FF Flow Automation",
				label: __("Flow"),
				change: () => {
					this.flow_name = this.rule_field.get_value();
					this.load();
				},
			},
			render_input: true,
		});
		if (this.flow_name) this.rule_field.set_value(this.flow_name);

		this.canvas = this.page.main.find("#ff-canvas")[0];
		this.svg = this.page.main.find("#ff-svg")[0];

		this.page.main.find("#ff-save").on("click", () => this.save());
		this.page.main.find("#ff-auto").on("click", () => this.auto_layout());
		this.page.main.find("#ff-connect").on("click", () => this.toggle_connect_mode());
		this.page.main.find("#ff-disconnect").on("click", () => this.remove_links());
		this.page.main.find(".ff-palette button").on("click", (e) => this.add_node(e.target.dataset.type));
		this.canvas.addEventListener("click", (e) => {
			if (e.target === this.canvas || e.target === this.svg) {
				this.connect_source = null;
				if (!this.connect_mode) this.selected = null;
				this.render();
			}
		});

		this.enable_drag();
		this.load();
	}

	load() {
		if (!this.flow_name) return;
		frappe.call({
			method: "frappe_flow.api.flow.get_flow_graph",
			args: { flow_name: this.flow_name },
			callback: (r) => {
				const data = r.message || {};
				let graph = data.flow_json;
				if (typeof graph === "string") {
					try { graph = JSON.parse(graph); } catch (e) { graph = null; }
				}
				if (graph && graph.nodes) {
					this.nodes = graph.nodes;
					this.edges = graph.edges || [];
				} else {
					this.nodes = [
						{ id: "trigger", type: "trigger", label: `${data.document_type || "Document"} ${data.trigger_event || ""}`, x: 80, y: 60 },
						{ id: "end", type: "end", label: __("Complete"), x: 80, y: 200 },
					];
					this.edges = [{ source: "trigger", target: "end" }];
				}
				this.render();
			},
		});
	}

	add_node(type) {
		const id = `${type}-${Date.now()}`;
		const y = 120 + this.nodes.length * 90;
		const labels = {
			condition: __("Condition"),
			send_email: __("Send Email"),
			send_whatsapp: __("Send WhatsApp"),
			create_task: __("Create Task"),
			assign_user: __("Assign User"),
			webhook: __("Webhook"),
			delay: __("Delay"),
			approval: __("Approval"),
			ai: __("AI Action"),
		};
		this.nodes.push({ id, type, label: labels[type] || type, x: 120, y, config: {} });
		if (this.selected) {
			this._link_nodes(this.selected, id, true);
		}
		this.selected = id;
		this.render();
		this.configure_node(this.nodes.find((n) => n.id === id));
	}

	_edge_exists(source, target) {
		return this.edges.some((e) => e.source === source && e.target === target);
	}

	_link_nodes(source, target, insert_between = false) {
		if (!source || !target || source === target) return;
		if (this._edge_exists(source, target)) return;

		if (insert_between) {
			const outgoing = this.edges.filter((e) => e.source === source);
			if (outgoing.length === 1 && outgoing[0].target !== target) {
				const old_target = outgoing[0].target;
				outgoing[0].target = target;
				if (!this._edge_exists(target, old_target)) {
					this.edges.push({ source: target, target: old_target });
				}
				frappe.show_alert({ message: __("Block inserted in flow"), indicator: "blue" });
				return;
			}
		}

		this.edges.push({ source, target });
		frappe.show_alert({ message: __("Blocks connected"), indicator: "green" });
	}

	toggle_connect_mode() {
		this.connect_mode = !this.connect_mode;
		this.connect_source = null;
		const btn = this.page.main.find("#ff-connect");
		btn.toggleClass("btn-primary", this.connect_mode);
		btn.toggleClass("btn-default", !this.connect_mode);
		const hint = this.page.main.find("#ff-hint");
		if (this.connect_mode) {
			hint.text(__("Connect mode: click the FROM block, then click the TO block."));
		} else {
			hint.text(__("Tip: Select a block, click Connect, then click the next block. Or select a block and add a new one to insert in between."));
		}
		this.render();
	}

	remove_links() {
		if (!this.selected) {
			frappe.msgprint(__("Select a block first, then click Remove Links."));
			return;
		}
		const before = this.edges.length;
		this.edges = this.edges.filter((e) => e.source !== this.selected && e.target !== this.selected);
		if (this.edges.length === before) {
			frappe.msgprint(__("This block has no connections."));
			return;
		}
		frappe.show_alert({ message: __("Connections removed"), indicator: "orange" });
		this.render();
	}

	handle_node_click(node) {
		this.selected = node.id;

		if (this.connect_mode) {
			if (!this.connect_source) {
				this.connect_source = node.id;
				this.render();
				frappe.show_alert({
					message: __("Now click the block to connect to"),
					indicator: "blue",
				});
				return;
			}
			this._link_nodes(this.connect_source, node.id);
			this.connect_source = null;
			this.connect_mode = false;
			this.page.main.find("#ff-connect").removeClass("btn-primary").addClass("btn-default");
			this.page.main.find("#ff-hint").text(
				__("Tip: Select a block, click Connect, then click the next block. Or select a block and add a new one to insert in between.")
			);
			this.render();
			return;
		}

		this.render();
		this.configure_node(node);
	}

	auto_layout() {
		let y = 60;
		this.nodes.forEach((n) => {
			n.x = 100;
			n.y = y;
			y += 100;
		});
		this.render();
	}

	render() {
		this.canvas.querySelectorAll(".ff-flow-node").forEach((el) => el.remove());
		this.nodes.forEach((node) => {
			const el = document.createElement("div");
			el.className = `ff-flow-node ${node.type}`;
			el.dataset.id = node.id;
			el.style.left = `${node.x}px`;
			el.style.top = `${node.y}px`;
			el.innerHTML = `<div class="ff-flow-node__type">${node.type}</div><div class="ff-flow-node__label">${frappe.utils.escape_html(node.label)}</div>`;
			if (this.selected === node.id) {
				el.classList.add("is-selected");
			}
			if (this.connect_source === node.id) {
				el.classList.add("is-connect-source");
			}
			el.addEventListener("click", (e) => {
				e.stopPropagation();
				this.handle_node_click(node);
			});
			this.canvas.appendChild(el);
		});
		this.draw_edges();
	}

	draw_edges() {
		this.svg.innerHTML = "";
		this.edges.forEach((edge) => {
			const a = this.nodes.find((n) => n.id === edge.source);
			const b = this.nodes.find((n) => n.id === edge.target);
			if (!a || !b) return;
			const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
			const x1 = a.x + 85;
			const y1 = a.y + 55;
			const x2 = b.x + 85;
			const y2 = b.y;
			line.setAttribute("d", `M ${x1} ${y1} C ${x1} ${y1 + 30}, ${x2} ${y2 - 30}, ${x2} ${y2}`);
			line.setAttribute("stroke", "#94a3b8");
			line.setAttribute("stroke-width", "2");
			line.setAttribute("fill", "none");
			this.svg.appendChild(line);
		});
	}

	configure_node(node) {
		const cfg = node.config || {};
		if (node.type === "condition") {
			frappe.prompt(
				[
					{ fieldname: "field_name", fieldtype: "Data", label: __("Field"), default: cfg.field_name },
					{ fieldname: "operator", fieldtype: "Select", label: __("Operator"), options: "=\n!=\n>\n<\n>=\n<=\ncontains\nin", default: cfg.operator || ">" },
					{ fieldname: "value", fieldtype: "Data", label: __("Value"), default: cfg.value },
				],
				(v) => {
					node.config = v;
					node.label = `${v.field_name} ${v.operator} ${v.value}`;
					this.render();
				},
				__("Configure Condition")
			);
		} else if (node.type === "send_email") {
			frappe.prompt(
				[
					{ fieldname: "to", fieldtype: "Data", label: __("To"), default: cfg.to || "{{doc.owner}}", description: __("Email or {{doc.field}} placeholder") },
					{ fieldname: "subject", fieldtype: "Data", label: __("Subject"), default: cfg.subject },
					{ fieldname: "message", fieldtype: "Small Text", label: __("Message"), default: cfg.message },
				],
				(v) => { node.config = v; node.label = __("Send Email"); this.render(); },
				__("Configure Email")
			);
		} else if (node.type === "send_whatsapp") {
			frappe.prompt(
				[
					{
						fieldname: "phone",
						fieldtype: "Data",
						label: __("Phone Number"),
						reqd: 1,
						default: cfg.phone || cfg.to || "{{doc.mobile_no}}",
						description: __("E.g. +919876543210 or {{doc.mobile_no}}"),
					},
					{
						fieldname: "message",
						fieldtype: "Small Text",
						label: __("Message"),
						reqd: 1,
						default: cfg.message,
						description: __("Use {{doc.field}} for document values"),
					},
					{
						fieldname: "provider",
						fieldtype: "Select",
						label: __("Provider"),
						options: "Twilio\nMeta Cloud API",
						default: cfg.provider === "Meta" ? "Meta Cloud API" : (cfg.provider || "Twilio"),
					},
					{
						fieldname: "credential",
						fieldtype: "Link",
						options: "FF Flow Credential",
						label: __("Credential"),
						reqd: 1,
						default: cfg.credential,
						description: __("Create FF Flow Credential with API keys first"),
					},
				],
				(v) => {
					node.config = v;
					const phone = (v.phone || "").trim();
					node.label = phone ? `${__("WhatsApp")} → ${phone}` : __("Send WhatsApp");
					this.render();
				},
				__("Configure WhatsApp")
			);
		} else if (node.type === "create_task") {
			frappe.prompt(
				[
					{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), default: cfg.description, reqd: 1 },
					{ fieldname: "assigned_to", fieldtype: "Data", label: __("Assign To"), default: cfg.assigned_to, description: __("User or {{doc.owner}}") },
					{ fieldname: "due_days", fieldtype: "Int", label: __("Due In (days)"), default: cfg.due_days || 3 },
					{ fieldname: "subject", fieldtype: "Data", label: __("Subject"), default: cfg.subject },
				],
				(v) => {
					node.config = v;
					node.label = v.subject || __("Create Task");
					this.render();
				},
				__("Configure Task")
			);
		} else if (node.type === "assign_user") {
			frappe.prompt(
				[
					{
						fieldname: "assigned_to",
						fieldtype: "Data",
						label: __("User"),
						reqd: 1,
						default: cfg.assigned_to || cfg.user || "{{doc.owner}}",
						description: __("Username or {{doc.field}} placeholder"),
					},
				],
				(v) => {
					node.config = v;
					node.label = v.assigned_to ? `${__("Assign")} ${v.assigned_to}` : __("Assign User");
					this.render();
				},
				__("Configure Assignment")
			);
		} else if (node.type === "webhook") {
			frappe.prompt(
				[
					{ fieldname: "url", fieldtype: "Data", label: __("Webhook URL"), reqd: 1, default: cfg.url },
					{
						fieldname: "payload",
						fieldtype: "Small Text",
						label: __("JSON Payload"),
						default: cfg.payload || '{"name": "{{doc.name}}"}',
						description: __("Optional JSON body with {{doc.field}} placeholders"),
					},
				],
				(v) => {
					node.config = v;
					node.label = __("Webhook");
					this.render();
				},
				__("Configure Webhook")
			);
		} else if (node.type === "delay") {
			frappe.prompt(
				[
					{ fieldname: "amount", fieldtype: "Int", label: __("Amount"), default: cfg.amount || 3 },
					{ fieldname: "unit", fieldtype: "Select", label: __("Unit"), options: "minutes\nhours\ndays\nweeks", default: cfg.unit || "days" },
				],
				(v) => { node.config = v; node.label = `${__("Wait")} ${v.amount} ${v.unit}`; this.render(); },
				__("Configure Delay")
			);
		} else if (node.type === "approval") {
			frappe.prompt(
				[
					{
						fieldname: "approval_rule",
						fieldtype: "Link",
						options: "DWB Approval Rule",
						label: __("Approval Rule"),
						default: cfg.approval_rule,
					},
				],
				(v) => {
					node.config = v;
					node.label = v.approval_rule || __("Approval");
					this.render();
				},
				__("Configure Approval")
			);
		} else if (node.type === "ai") {
			frappe.prompt(
				[
					{
						fieldname: "ai_action",
						fieldtype: "Select",
						label: __("AI Action"),
						options: "summarize\ndraft_email\nclassify",
						default: cfg.ai_action || "summarize",
					},
					{ fieldname: "prompt", fieldtype: "Small Text", label: __("Prompt"), default: cfg.prompt },
				],
				(v) => {
					node.config = v;
					node.label = __("AI Action");
					this.render();
				},
				__("Configure AI")
			);
		}
	}

	enable_drag() {
		let active = null;
		let ox = 0;
		let oy = 0;
		this.canvas.addEventListener("mousedown", (e) => {
			const el = e.target.closest(".ff-flow-node");
			if (!el) return;
			active = this.nodes.find((n) => n.id === el.dataset.id);
			ox = e.clientX - el.offsetLeft;
			oy = e.clientY - el.offsetTop;
		});
		document.addEventListener("mousemove", (e) => {
			if (!active) return;
			const rect = this.canvas.getBoundingClientRect();
			active.x = e.clientX - rect.left - ox + this.canvas.scrollLeft;
			active.y = e.clientY - rect.top - oy + this.canvas.scrollTop;
			const el = this.canvas.querySelector(`[data-id="${active.id}"]`);
			if (el) {
				el.style.left = `${active.x}px`;
				el.style.top = `${active.y}px`;
			}
			this.draw_edges();
		});
		document.addEventListener("mouseup", () => { active = null; });
	}

	save() {
		if (!this.flow_name) return frappe.msgprint(__("Select a flow first."));
		frappe.call({
			method: "frappe_flow.api.flow.save_flow_graph",
			args: { flow_name: this.flow_name, flow_json: { nodes: this.nodes, edges: this.edges } },
			callback() {
				frappe.show_alert({ message: __("Flow saved"), indicator: "green" });
			},
		});
	}
};
