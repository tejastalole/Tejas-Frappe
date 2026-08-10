frappe.ui.form.on("BOQ", {
	refresh(frm) {
		render_rate_summary(frm);

		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Load Rate Buildup Template"), () => {
				frappe.call({
					method: "boq_management.boq_management.doctype.boq.boq.load_rate_buildup_template",
					callback(r) {
						frm.clear_table("items");
						(r.message || []).forEach((row) => {
							const child = frm.add_child("items");
							Object.assign(child, row);
						});
						frm.refresh_field("items");
						recalculate_boq(frm);
						frappe.show_alert({ message: __("Rate buildup template loaded"), indicator: "green" });
					},
				});
			}, __("Templates"));

			frm.add_custom_button(__("Load Category Template"), () => {
				if (!frm.doc.boq_category) {
					frappe.msgprint(__("Select Primary Category first."));
					return;
				}
				frappe.call({
					method: "boq_management.boq_management.doctype.boq.boq.load_category_template",
					args: { boq_category: frm.doc.boq_category },
					callback(r) {
						(r.message || []).forEach((row) => {
							const child = frm.add_child("items");
							Object.assign(child, row);
						});
						frm.refresh_field("items");
						recalculate_boq(frm);
						frappe.show_alert({ message: __("Template loaded"), indicator: "green" });
					},
				});
			}, __("Templates"));
		}
	},

	onload(frm) {
		frm.set_query("boq_sub_category", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			if (row.boq_category) {
				return { filters: { boq_category: row.boq_category, is_active: 1 } };
			}
		});

		frm.set_query("boq_item_master", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			const filters = { is_active: 1 };
			if (row.boq_category) filters.boq_category = row.boq_category;
			if (row.boq_sub_category) filters.boq_sub_category = row.boq_sub_category;
			return { filters };
		});
	},

	overhead_percent(frm) {
		recalculate_boq(frm);
	},

	contractor_profit_percent(frm) {
		recalculate_boq(frm);
	},

	items_add(frm) {
		recalculate_boq(frm);
	},

	items_remove(frm) {
		recalculate_boq(frm);
	},
});

frappe.ui.form.on("BOQ Item", {
	boq_category(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "boq_sub_category", "");
		frappe.model.set_value(cdt, cdn, "boq_item_master", "");
	},

	boq_sub_category(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "boq_item_master", "");
	},

	boq_item_master(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.boq_item_master) return;
		frappe.db.get_value(
			"BOQ Item Master",
			row.boq_item_master,
			["item_name", "specification", "default_uom", "default_rate", "boq_category", "boq_sub_category"],
			(r) => {
				frappe.model.set_value(cdt, cdn, "item_description", r.item_name);
				frappe.model.set_value(cdt, cdn, "specification", r.specification);
				frappe.model.set_value(cdt, cdn, "uom", r.default_uom);
				frappe.model.set_value(cdt, cdn, "rate", r.default_rate);
				if (!row.boq_category) frappe.model.set_value(cdt, cdn, "boq_category", r.boq_category);
				if (!row.boq_sub_category) frappe.model.set_value(cdt, cdn, "boq_sub_category", r.boq_sub_category);
			}
		);
	},

	qty(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},

	rate(frm, cdt, cdn) {
		calculate_row_amount(frm, cdt, cdn);
	},
});

function calculate_row_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	row.amount = flt(row.qty) * flt(row.rate);
	frm.refresh_field("items");
	recalculate_boq(frm);
}

function recalculate_boq(frm) {
	let sub_total = 0;
	(frm.doc.items || []).forEach((row) => {
		row.amount = flt(row.qty) * flt(row.rate);
		sub_total += flt(row.amount);
	});

	const overhead_pct = flt(frm.doc.overhead_percent);
	const profit_pct = flt(frm.doc.contractor_profit_percent);
	const overhead_amount = sub_total * overhead_pct / 100;
	const profit_amount = sub_total * profit_pct / 100;
	const final_rate = sub_total + overhead_amount + profit_amount;

	frm.set_value("sub_total", sub_total);
	frm.set_value("overhead_amount", overhead_amount);
	frm.set_value("contractor_profit_amount", profit_amount);
	frm.set_value("final_rate", final_rate);
	frm.set_value("total_cost", final_rate);
	render_rate_summary(frm);
}

function render_rate_summary(frm) {
	const wrapper = frm.fields_dict.rate_summary_html?.$wrapper;
	if (!wrapper) return;

	const rows = frm.doc.items || [];
	const fmt = (v) => format_currency(v, frm.doc.currency || frappe.defaults.get_default("currency"));

	let html = `<div class="boq-rate-summary"><table>
		<thead><tr>
			<th>Component</th><th>Unit</th><th class="num">Qty</th>
			<th class="num">Rate (₹)</th><th class="num">Amount (₹)</th>
		</tr></thead><tbody>`;

	rows.forEach((row) => {
		html += `<tr>
			<td>${frappe.utils.escape_html(row.item_description || "")}</td>
			<td>${frappe.utils.escape_html(row.uom || "")}</td>
			<td class="num">${flt(row.qty).toFixed(2)}</td>
			<td class="num">${fmt(row.rate)}</td>
			<td class="num">${fmt(row.amount)}</td>
		</tr>`;
	});

	const uom = frm.doc.final_rate_uom || "m2";
	html += `</tbody></table><table>
		<tbody>
			<tr class="summary-row"><td colspan="4">Sub Total</td><td class="num">${fmt(frm.doc.sub_total)}</td></tr>
			<tr class="summary-row"><td colspan="4">Overheads (${flt(frm.doc.overhead_percent)}%)</td><td class="num">${fmt(frm.doc.overhead_amount)}</td></tr>
			<tr class="summary-row"><td colspan="4">Contractor Profit (${flt(frm.doc.contractor_profit_percent)}%)</td><td class="num">${fmt(frm.doc.contractor_profit_amount)}</td></tr>
			<tr class="final-row"><td colspan="3">Final Rate <span class="per-unit">Per ${frappe.utils.escape_html(uom)}</span></td><td class="num"></td><td class="num">₹${format_number(frm.doc.final_rate, null, 0)}</td></tr>
		</tbody></table></div>`;

	wrapper.html(html);
}
