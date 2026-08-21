// Copyright (c) 2026, Tejas and contributors
// MIT License

frappe.pages["currency-info-live"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Currency Info Live"),
		single_column: true,
	});

	page.set_secondary_action(__("Settings"), () => {
		frappe.set_route("Form", "Currency Info Settings");
	});

	new currencyinfo.LiveFeed(page);
};

frappe.provide("currencyinfo");

currencyinfo.LiveFeed = class LiveFeed {
	constructor(page) {
		this.page = page;
		this.ws = null;
		this.reconnect_timer = null;
		this.trades = [];
		this.max_rows = 40;
		this.last_price = null;
		this.make();
		this.boot();
	}

	make() {
		this.$root = $(`
			<div class="ci-live">
				<div class="ci-live__hero">
					<div class="ci-live__meta">
						<div class="ci-live__eyebrow">Binance Spot · Real-time</div>
						<div class="ci-live__symbol" data-symbol>BTCUSDT</div>
						<div class="ci-live__status">
							<span class="ci-live__dot" data-dot></span>
							<span data-status>Connecting…</span>
						</div>
					</div>
					<div class="ci-live__price-block">
						<div class="ci-live__price" data-price>—</div>
						<div class="ci-live__change" data-change></div>
					</div>
					<div class="ci-live__stats">
						<div class="ci-live__stat">
							<div class="ci-live__stat-label">Last Qty</div>
							<div class="ci-live__stat-value" data-qty>—</div>
						</div>
						<div class="ci-live__stat">
							<div class="ci-live__stat-label">Side</div>
							<div class="ci-live__stat-value" data-side>—</div>
						</div>
						<div class="ci-live__stat">
							<div class="ci-live__stat-label">Trade Time</div>
							<div class="ci-live__stat-value" data-time>—</div>
						</div>
						<div class="ci-live__stat">
							<div class="ci-live__stat-label">Trade ID</div>
							<div class="ci-live__stat-value" data-trade-id>—</div>
						</div>
					</div>
				</div>
				<div class="ci-live__panel">
					<div class="ci-live__panel-head">
						<div class="ci-live__panel-title">Recent trades</div>
						<div class="ci-live__panel-sub" data-url></div>
					</div>
					<div class="ci-live__table-wrap">
						<table class="ci-live__table">
							<thead>
								<tr>
									<th>Time</th>
									<th>Side</th>
									<th>Price</th>
									<th>Quantity</th>
									<th>Notional</th>
									<th>Trade ID</th>
								</tr>
							</thead>
							<tbody data-tbody></tbody>
						</table>
					</div>
				</div>
			</div>
		`).appendTo(this.page.main);

		this.$price = this.$root.find("[data-price]");
		this.$change = this.$root.find("[data-change]");
		this.$qty = this.$root.find("[data-qty]");
		this.$side = this.$root.find("[data-side]");
		this.$time = this.$root.find("[data-time]");
		this.$tradeId = this.$root.find("[data-trade-id]");
		this.$symbol = this.$root.find("[data-symbol]");
		this.$status = this.$root.find("[data-status]");
		this.$dot = this.$root.find("[data-dot]");
		this.$url = this.$root.find("[data-url]");
		this.$tbody = this.$root.find("[data-tbody]");
	}

	boot() {
		frappe.call({
			method: "currencyinfo.currency_info.stream.get_client_config",
			callback: (r) => {
				const cfg = r.message || {};
				this.stream_url = cfg.stream_url;
				this.symbol = cfg.symbol || "BTCUSDT";
				this.$symbol.text(this.symbol);
				this.$url.text(this.stream_url || "");
				if (cfg.latest) {
					this.apply_tick(cfg.latest, false);
				}
				this.connect_binance();
				this.listen_frappe_realtime(cfg.realtime_event || "currencyinfo_trade");
			},
		});
	}

	set_status(text, state) {
		this.$status.text(text);
		this.$dot.attr("data-state", state || "idle");
	}

	connect_binance() {
		if (!this.stream_url) {
			this.set_status(__("No stream URL configured"), "error");
			return;
		}
		if (this.ws) {
			try {
				this.ws.close();
			} catch (e) {
				/* ignore */
			}
		}

		this.set_status(__("Connecting to Binance…"), "connecting");
		const ws = new WebSocket(this.stream_url);
		this.ws = ws;

		ws.onopen = () => {
			this.set_status(__("Live · Binance WebSocket"), "live");
		};

		ws.onmessage = (event) => {
			try {
				const payload = JSON.parse(event.data);
				if (payload.e !== "trade") {
					return;
				}
				const tick = this.normalize(payload);
				this.apply_tick(tick, true);
			} catch (e) {
				/* ignore bad frames */
			}
		};

		ws.onerror = () => {
			this.set_status(__("WebSocket error"), "error");
		};

		ws.onclose = () => {
			this.set_status(__("Disconnected · reconnecting…"), "idle");
			clearTimeout(this.reconnect_timer);
			this.reconnect_timer = setTimeout(() => this.connect_binance(), 2000);
		};
	}

	listen_frappe_realtime(event_name) {
		frappe.realtime.on(event_name, (tick) => {
			// Backup channel from server streamer; skip if browser already live
			if (this.ws && this.ws.readyState === WebSocket.OPEN) {
				return;
			}
			this.apply_tick(tick, true);
		});
	}

	normalize(payload) {
		const price = parseFloat(payload.p || 0);
		const quantity = parseFloat(payload.q || 0);
		const is_buyer_maker = !!payload.m;
		return {
			symbol: payload.s,
			trade_id: String(payload.t || ""),
			price,
			quantity,
			quote_qty: price * quantity,
			side: is_buyer_maker ? "Sell" : "Buy",
			trade_time: payload.T
				? new Date(payload.T).toLocaleString()
				: "",
			trade_time_raw: payload.T,
		};
	}

	apply_tick(tick, prepend) {
		if (!tick) {
			return;
		}
		const price = Number(tick.price || 0);
		const prev = this.last_price;
		this.last_price = price;

		this.$price.text(this.format_price(price));
		this.$qty.text(this.format_qty(tick.quantity));
		this.$side
			.text(tick.side || "—")
			.toggleClass("is-buy", tick.side === "Buy")
			.toggleClass("is-sell", tick.side === "Sell");
		this.$time.text(tick.trade_time || "—");
		this.$tradeId.text(tick.trade_id || "—");

		if (prev != null && price !== prev) {
			const up = price > prev;
			this.$change
				.text(up ? "▲ up" : "▼ down")
				.toggleClass("is-up", up)
				.toggleClass("is-down", !up);
			this.$price.toggleClass("flash-up", up).toggleClass("flash-down", !up);
			setTimeout(() => this.$price.removeClass("flash-up flash-down"), 350);
		}

		if (prepend) {
			this.trades.unshift(tick);
			this.trades = this.trades.slice(0, this.max_rows);
			this.render_table();
		}
	}

	render_table() {
		const rows = this.trades
			.map((t) => {
				const side_class = t.side === "Buy" ? "is-buy" : "is-sell";
				return `<tr>
					<td>${frappe.utils.escape_html(String(t.trade_time || ""))}</td>
					<td class="${side_class}">${frappe.utils.escape_html(t.side || "")}</td>
					<td class="ci-mono">${this.format_price(t.price)}</td>
					<td class="ci-mono">${this.format_qty(t.quantity)}</td>
					<td class="ci-mono">${this.format_price(t.quote_qty || t.price * t.quantity)}</td>
					<td class="ci-mono ci-muted">${frappe.utils.escape_html(String(t.trade_id || ""))}</td>
				</tr>`;
			})
			.join("");
		this.$tbody.html(rows);
	}

	format_price(v) {
		const n = Number(v || 0);
		return n.toLocaleString(undefined, {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		});
	}

	format_qty(v) {
		const n = Number(v || 0);
		return n.toLocaleString(undefined, {
			minimumFractionDigits: 4,
			maximumFractionDigits: 6,
		});
	}
};
