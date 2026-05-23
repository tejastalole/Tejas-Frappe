frappe.provide("ai_bot");

const AI_BOT_STORAGE_KEY = "ai_bot_conversation_id";
const AI_BOT_UI_VERSION = 5;
const AI_BOT_POSITION_KEY = "ai_bot_panel_position";

ai_bot.ChatDashboard = class {
	constructor() {
		this.$wrapper = null;
		this.is_open = false;
		this.conversation_id = localStorage.getItem(AI_BOT_STORAGE_KEY) || null;
	}

	toggle() {
		if (this.is_open) {
			this.close();
		} else {
			this.open();
		}
	}

	open() {
		this._remove_legacy_ui();

		if (this.$wrapper && this.$wrapper.data("ui-version") !== AI_BOT_UI_VERSION) {
			this.$wrapper.remove();
			this.$wrapper = null;
		}

		if (!this.$wrapper) {
			this.render();
			if (this.conversation_id) {
				this.load_history();
			} else {
				this.show_welcome();
			}
		}
		this.$wrapper.removeClass("hidden");
		this.is_open = true;
		this.$input.focus();
	}

	_remove_legacy_ui() {
		$(".ai-bot-suggestions-wrap, .ai-bot-suggestions-header, .ai-bot-chips-grid").remove();
	}

	close() {
		if (this.$wrapper) {
			this.$wrapper.addClass("hidden");
		}
		this.is_open = false;
	}

	render() {
		this.$wrapper = $(`
			<div class="ai-bot-overlay hidden">
				<div class="ai-bot-panel">
					<div class="ai-bot-header">
						<div class="ai-bot-header-left">
							<div class="ai-bot-avatar">
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 12 2z"/>
									<circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/>
									<path d="M9 17h6"/>
								</svg>
							</div>
							<div>
								<div class="ai-bot-title">${__("AI Bot")}</div>
								<div class="ai-bot-subtitle">${__("Ask about your ERP data")}</div>
							</div>
						</div>
						<div class="ai-bot-header-actions">
							<button class="btn btn-reset ai-bot-new-chat" title="${__("New chat")}">
								<svg class="icon icon-sm"><use href="#icon-add"></use></svg>
							</button>
							<button class="btn btn-reset ai-bot-close" title="${__("Close")}">
								<svg class="icon icon-sm"><use href="#icon-close"></use></svg>
							</button>
						</div>
					</div>
					<div class="ai-bot-messages"></div>
					<div class="ai-bot-footer">
						<div class="ai-bot-input-area">
							<input
								type="text"
								class="ai-bot-input"
								placeholder="${__("Type your question...")}"
								autocomplete="off"
							/>
							<button class="ai-bot-send" title="${__("Send")}" type="button" aria-label="${__("Send")}">
								<svg class="ai-bot-send-icon" viewBox="0 0 24 24" aria-hidden="true">
									<path fill="#ffffff" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
								</svg>
							</button>
						</div>
					</div>
				</div>
			</div>
		`).appendTo("body");

		this.$wrapper.data("ui-version", AI_BOT_UI_VERSION);
		this.$panel = this.$wrapper.find(".ai-bot-panel");
		this.$header = this.$wrapper.find(".ai-bot-header");
		this.$messages = this.$wrapper.find(".ai-bot-messages");
		this.$input = this.$wrapper.find(".ai-bot-input");
		this._apply_saved_position();
		this.bind_events();
		this._setup_drag();
	}

	bind_events() {
		this.$wrapper.find(".ai-bot-close").on("click", () => this.close());
		this.$wrapper.find(".ai-bot-new-chat").on("click", () => this.new_chat());
		this.$wrapper.find(".ai-bot-send").on("click", () => this.send());
		this.$input.on("keydown", (e) => {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				this.send();
			}
		});
	}

	show_welcome() {
		frappe.call({
			method: "ai_bot.api.chat.get_welcome",
			callback: (r) => {
				this.append_message(r.message || this._default_welcome(), "bot");
			},
			error: () => {
				this.append_message(this._default_welcome(), "bot");
			},
		});
	}

	_default_welcome() {
		return __(
			"<p><b>AI ERP Copilot</b> — ask in English or Hindi.</p>" +
				"<p><b>Try:</b></p>" +
				"<ul>" +
				"<li><i>Show pending purchase orders</i></li>" +
				"<li><i>Pending approvals दिखाओ</i></li>" +
				"<li><i>Unpaid invoices above 1 lakh</i></li>" +
				"<li><i>Create lead Rahul from Pune</i></li>" +
				"<li><i>Approve PO-00012</i></li>" +
				"<li><i>Low stock items</i></li>" +
				"</ul>"
		);
	}

	new_chat() {
		this.conversation_id = null;
		localStorage.removeItem(AI_BOT_STORAGE_KEY);
		this.$messages.empty();
		this.show_welcome();
	}

	load_history() {
		frappe.call({
			method: "ai_bot.api.chat.get_conversation",
			args: { conversation_id: this.conversation_id },
			callback: (r) => {
				if (!r.message || !r.message.messages) {
					this.show_welcome();
					return;
				}
				this.$messages.empty();
				r.message.messages.forEach((m) => {
					this.append_message(m.content, m.role, m.actions || []);
				});
			},
			error: () => {
				localStorage.removeItem(AI_BOT_STORAGE_KEY);
				this.conversation_id = null;
				this.show_welcome();
			},
		});
	}

	send(message_text) {
		const message = (message_text || this.$input.val()).trim();
		if (!message) return;

		this.append_message(message, "user");
		this.$input.val("");
		this.append_typing();

		frappe.call({
			method: "ai_bot.api.chat.ask",
			args: {
				message,
				conversation_id: this.conversation_id,
			},
			callback: (r) => {
				this.remove_typing();
				if (!r.message) return;

				if (r.message.conversation_id) {
					this.conversation_id = r.message.conversation_id;
					localStorage.setItem(AI_BOT_STORAGE_KEY, this.conversation_id);
				}

				if (r.message.reply) {
					this.append_message(r.message.reply, "bot", r.message.actions || []);
				}
			},
			error: () => {
				this.remove_typing();
				this.append_message(__("Something went wrong. Please try again."), "bot");
			},
		});
	}

	append_message(text, role, actions = []) {
		const $bubble = $(`<div class="ai-bot-bubble">${text}</div>`);

		if (actions && actions.length) {
			const $actions = $('<div class="ai-bot-actions"></div>');
			actions.forEach((action) => {
				const $btn = $(
					`<button type="button" class="btn btn-xs btn-default ai-bot-action-btn">${frappe.utils.escape_html(action.label)}</button>`
				);
				$btn.on("click", () => this.run_action(action));
				$actions.append($btn);
			});
			$bubble.append($actions);
		}

		const $msg = $(`<div class="ai-bot-message ${role}"></div>`).append($bubble);
		this.$messages.append($msg);
		this.scroll_to_bottom();
	}

	run_action(action) {
		if (!action || !action.type) return;

		if (action.type === "list") {
			frappe.route_options = action.filters || {};
			frappe.set_route("List", action.doctype);
		} else if (action.type === "create") {
			frappe.new_doc(action.doctype);
		} else if (action.type === "form" || action.type === "open") {
			frappe.set_route("Form", action.doctype, action.name);
		}
		this.close();
	}

	append_typing() {
		this.$typing = $(`
			<div class="ai-bot-message bot ai-bot-typing-indicator">
				<div class="ai-bot-bubble">
					<span></span><span></span><span></span>
				</div>
			</div>
		`);
		this.$messages.append(this.$typing);
		this.scroll_to_bottom();
	}

	remove_typing() {
		if (this.$typing) {
			this.$typing.remove();
			this.$typing = null;
		}
	}

	scroll_to_bottom() {
		this.$messages.scrollTop(this.$messages[0].scrollHeight);
	}

	_apply_saved_position() {
		try {
			const saved = JSON.parse(localStorage.getItem(AI_BOT_POSITION_KEY) || "null");
			if (saved && typeof saved.left === "number" && typeof saved.top === "number") {
				this.$panel.css({ left: saved.left, top: saved.top, right: "auto", bottom: "auto" });
			}
		} catch (e) {
			/* ignore invalid saved position */
		}
	}

	_save_position() {
		const rect = this.$panel[0].getBoundingClientRect();
		localStorage.setItem(
			AI_BOT_POSITION_KEY,
			JSON.stringify({ left: Math.round(rect.left), top: Math.round(rect.top) })
		);
	}

	_clamp_panel(left, top) {
		const panel = this.$panel[0];
		const maxLeft = Math.max(8, window.innerWidth - panel.offsetWidth - 8);
		const maxTop = Math.max(8, window.innerHeight - panel.offsetHeight - 8);
		return {
			left: Math.min(Math.max(8, left), maxLeft),
			top: Math.min(Math.max(8, top), maxTop),
		};
	}

	_setup_drag() {
		let dragging = false;
		let startX = 0;
		let startY = 0;
		let startLeft = 0;
		let startTop = 0;

		const on_move = (e) => {
			if (!dragging) return;
			const clientX = e.touches ? e.touches[0].clientX : e.clientX;
			const clientY = e.touches ? e.touches[0].clientY : e.clientY;
			const next = this._clamp_panel(
				startLeft + (clientX - startX),
				startTop + (clientY - startY)
			);
			this.$panel.css({
				left: next.left,
				top: next.top,
				right: "auto",
				bottom: "auto",
			});
		};

		const on_end = () => {
			if (!dragging) return;
			dragging = false;
			this.$header.removeClass("ai-bot-dragging");
			$(document).off(".ai_bot_drag");
			this._save_position();
		};

		this.$header.on("mousedown touchstart", (e) => {
			if ($(e.target).closest("button").length) return;

			const point = e.touches ? e.touches[0] : e;
			const rect = this.$panel[0].getBoundingClientRect();

			dragging = true;
			startX = point.clientX;
			startY = point.clientY;
			startLeft = rect.left;
			startTop = rect.top;

			this.$panel.css({
				left: startLeft,
				top: startTop,
				right: "auto",
				bottom: "auto",
			});
			this.$header.addClass("ai-bot-dragging");

			$(document).on("mousemove.ai_bot_drag touchmove.ai_bot_drag", on_move);
			$(document).on("mouseup.ai_bot_drag touchend.ai_bot_drag", on_end);
			e.preventDefault();
		});
	}
};

ai_bot.dashboard = null;

function ai_bot_toggle_chat() {
	if (!ai_bot.dashboard) {
		ai_bot.dashboard = new ai_bot.ChatDashboard();
	}
	ai_bot.dashboard.toggle();
}

function ai_bot_reset_stale_overlay() {
	if (
		ai_bot.dashboard &&
		ai_bot.dashboard.$wrapper &&
		ai_bot.dashboard.$wrapper.data("ui-version") !== AI_BOT_UI_VERSION
	) {
		$(".ai-bot-overlay").remove();
		ai_bot.dashboard = null;
	}
}

const AI_BOT_ICON_SVG = `
	<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="ai-bot-nav-icon" aria-hidden="true">
		<path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 12 2z"/>
		<circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/>
		<path d="M9 17h6"/>
	</svg>
`;

function ai_bot_bind_open($el) {
	return $el.on("click", (e) => {
		e.preventDefault();
		e.stopPropagation();
		ai_bot_toggle_chat();
	});
}

function ai_bot_get_navbar_button() {
	return ai_bot_bind_open($(`
		<button
			id="ai-bot-navbar-btn"
			type="button"
			class="btn btn-reset ai-bot-nav-btn"
			title="${__("AI Bot")}"
		>
			${AI_BOT_ICON_SVG}
			<span class="ai-bot-nav-label">${__("AI Bot")}</span>
		</button>
	`));
}

function ai_bot_remove_fab() {
	$("#ai-bot-fab").remove();
}

function ai_bot_mount_navbar_button() {
	ai_bot_remove_fab();

	const $existing = $("#ai-bot-navbar-btn");
	if ($existing.length) {
		if ($.contains(document.documentElement, $existing[0])) {
			return true;
		}
		$existing.remove();
	}

	const $header = $("header.navbar, header").first();
	if (!$header.length) {
		return false;
	}

	const $btn = ai_bot_get_navbar_button();

	// First button in navbar, immediately before the awesome bar
	const $search_bar = $header.find(".search-bar").first();
	if ($search_bar.length) {
		$search_bar.before($btn);
		return true;
	}

	const $search_form = $header.find('form[role="search"]').first();
	if ($search_form.length) {
		$search_form.prepend($btn);
		return true;
	}

	return false;
}

function ai_bot_init_ui() {
	ai_bot_reset_stale_overlay();
	ai_bot_mount_navbar_button();
}

function ai_bot_schedule_ui_mount() {
	ai_bot_init_ui();
	let attempts = 0;
	const timer = setInterval(() => {
		ai_bot_init_ui();
		if (++attempts >= 48) {
			clearInterval(timer);
		}
	}, 250);
}

function ai_bot_on_ready(fn) {
	if (typeof frappe !== "undefined" && typeof frappe.ready === "function") {
		frappe.ready(fn);
		return;
	}
	$(fn);
}

$(document).on("toolbar_setup app_ready startup", ai_bot_init_ui);
$(document).on("page-change", ai_bot_init_ui);

ai_bot_on_ready(ai_bot_schedule_ui_mount);

// Run as soon as the script loads (desk may not fire frappe.ready)
if (document.body) {
	ai_bot_init_ui();
} else {
	document.addEventListener("DOMContentLoaded", ai_bot_init_ui);
}
