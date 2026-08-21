// Copyright (c) 2026, Tejas and contributors
// MIT License

frappe.query_reports["Easy TimePro Daily Attendance"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
			width: "80px",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			width: "80px",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => ({
				filters: { status: "Active" },
			}),
		},
		{
			fieldname: "emp_code",
			label: __("Employee ID"),
			fieldtype: "Data",
		},
	],

	get_datatable_options(options) {
		options.layout = "fluid";
		options.cellHeight = 36;
		options.columns = (options.columns || []).map((col) => {
			const id = col.id || col.fieldname;
			if (id === "employee") {
				return Object.assign({}, col, { width: 200 });
			}
			if (id === "emp_code") {
				// Keep Employee ID compact; don't stretch with fluid layout
				return Object.assign({}, col, { width: 100, resizable: false });
			}
			return col;
		});
		return options;
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) {
			return value;
		}

		if (column.fieldname === "employee_name") {
			return `<span class="etp-name">${frappe.utils.escape_html(data.employee_name || "")}</span>`;
		}

		if (column.fieldname === "emp_code") {
			return `<span class="etp-code">${frappe.utils.escape_html(data.emp_code || "")}</span>`;
		}

		if (column.fieldname === "department") {
			if (!data.department) {
				return `<span class="etp-muted">—</span>`;
			}
			return `<span class="etp-dept">${frappe.utils.escape_html(data.department)}</span>`;
		}

		if (column.fieldname === "day_status") {
			const tone =
				{
					Complete: "green",
					"Checked In": "blue",
					"Checked Out": "orange",
					"No IN/OUT": "gray",
				}[data.day_status] || "gray";
			return `<span class="etp-pill etp-pill--${tone}">${frappe.utils.escape_html(
				data.day_status || ""
			)}</span>`;
		}

		if (column.fieldname === "first_in") {
			if (!data.first_in || data.first_in === "—") {
				return `<span class="etp-muted">—</span>`;
			}
			return `<span class="etp-punch etp-punch--in"><span class="etp-punch__label">IN</span>${frappe.utils.escape_html(
				data.first_in
			)}</span>`;
		}

		if (column.fieldname === "last_out") {
			if (!data.last_out || data.last_out === "—") {
				return `<span class="etp-muted">—</span>`;
			}
			return `<span class="etp-punch etp-punch--out"><span class="etp-punch__label">OUT</span>${frappe.utils.escape_html(
				data.last_out
			)}</span>`;
		}

		if (column.fieldname === "work_hours") {
			const hours = Number(data.work_hours || 0);
			if (!hours) {
				return `<span class="etp-muted">0.00h</span>`;
			}
			const tone = hours >= 8 ? "good" : hours >= 4 ? "ok" : "low";
			const width = Math.min(100, Math.round((hours / 10) * 100));
			return `<div class="etp-hours">
				<div class="etp-hours__bar"><span style="width:${width}%" class="etp-hours__fill etp-hours__fill--${tone}"></span></div>
				<span class="etp-hours__val">${hours.toFixed(2)}h</span>
			</div>`;
		}

		return value;
	},

	onload(report) {
		const old = document.getElementById("etp-daily-att-style");
		if (old) {
			old.remove();
		}
		if (!document.getElementById("etp-daily-att-style-v2")) {
			const style = document.createElement("style");
			style.id = "etp-daily-att-style-v2";
			style.textContent = `
				.etp-report-banner {
					margin: 4px 0 14px;
					padding: 14px 16px;
					border-radius: 10px;
					border: 1px solid #e4e7ec;
					border-left: 4px solid #1f4b99;
					background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
					box-shadow: 0 1px 2px rgba(16,24,40,0.04);
				}
				.etp-report-banner__title {
					font-size: 15px;
					font-weight: 700;
					color: #101828;
					margin-bottom: 4px;
				}
				.etp-report-banner__meta {
					font-size: 12px;
					color: #667085;
				}
				.etp-name { font-weight: 650; color: #101828; }
				.etp-code {
					font-variant-numeric: tabular-nums;
					font-size: 12px;
					color: #475467;
					background: #f2f4f7;
					border: 1px solid #e4e7ec;
					border-radius: 6px;
					padding: 1px 7px;
				}
				.etp-dept { color: #344054; font-size: 12.5px; }
				.etp-muted { color: #98a2b3; }
				.etp-pill {
					display: inline-flex;
					align-items: center;
					padding: 1px 8px;
					border-radius: 999px;
					font-size: 11px;
					font-weight: 600;
					line-height: 1.35;
					border: 1px solid transparent;
					white-space: nowrap;
					vertical-align: middle;
				}
				.etp-pill--green { background: #ecfdf3; color: #067647; border-color: #abefc6; }
				.etp-pill--blue { background: #eff4ff; color: #175cd3; border-color: #b2ccff; }
				.etp-pill--orange { background: #fffaeb; color: #b54708; border-color: #fedf89; }
				.etp-pill--gray { background: #f2f4f7; color: #344054; border-color: #d0d5dd; }
				.etp-punch {
					display: inline-flex;
					align-items: center;
					gap: 6px;
					font-weight: 650;
					font-variant-numeric: tabular-nums;
					font-size: 13px;
				}
				.etp-punch__label {
					font-size: 10px;
					font-weight: 700;
					letter-spacing: 0.04em;
					padding: 1px 5px;
					border-radius: 4px;
				}
				.etp-punch--in { color: #175cd3; }
				.etp-punch--in .etp-punch__label { background: #eff4ff; color: #175cd3; }
				.etp-punch--out { color: #b42318; }
				.etp-punch--out .etp-punch__label { background: #fef3f2; color: #b42318; }
				.etp-hours {
					display: flex;
					align-items: center;
					gap: 8px;
					width: 100%;
					min-width: 110px;
					max-width: 180px;
				}
				.etp-hours__bar {
					flex: 1;
					height: 6px;
					border-radius: 99px;
					background: #eef2f6;
					overflow: hidden;
				}
				.etp-hours__fill {
					display: block;
					height: 100%;
					border-radius: 99px;
				}
				.etp-hours__fill--good { background: #12b76a; }
				.etp-hours__fill--ok { background: #2e90fa; }
				.etp-hours__fill--low { background: #f79009; }
				.etp-hours__val {
					font-weight: 700;
					font-variant-numeric: tabular-nums;
					color: #1f4b99;
					font-size: 12px;
					min-width: 42px;
				}
				.report-wrapper .datatable,
				.report-wrapper .dt-scrollable {
					width: 100% !important;
				}
				.report-summary {
					gap: 10px !important;
				}
				.report-summary > div {
					border-radius: 10px !important;
					border: 1px solid #e4e7ec !important;
					box-shadow: 0 1px 2px rgba(16,24,40,0.04);
					background: #fff !important;
				}
			`;
			document.head.appendChild(style);
		}

		report.page.add_inner_button(__("Punch Logs"), () => {
			frappe.set_route("List", "Easy TimePro Punch Log");
		});
		report.page.add_inner_button(__("Employee Checkin"), () => {
			frappe.set_route("List", "Employee Checkin");
		});
	},
};
