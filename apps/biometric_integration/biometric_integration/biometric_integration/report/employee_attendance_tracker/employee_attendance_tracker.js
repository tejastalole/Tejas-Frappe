// Copyright (c) 2026, Tejas and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Attendance Tracker"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => {
				const company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						status: "Active",
						...(company ? { company } : {}),
					},
				};
			},
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Completed", "In Progress", "Incomplete", "Not Started"],
		},
		{
			fieldname: "late_only",
			label: __("Late Only"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) {
			return value;
		}

		if (column.fieldname === "final_status") {
			const status = data.final_status || "";
			const tone = {
				Completed: "green",
				"In Progress": "blue",
				Incomplete: "orange",
				"Not Started": "gray",
			}[status] || "gray";
			return `<span class="bio-att-pill bio-att-pill--${tone}">${frappe.utils.escape_html(
				status
			)}</span>`;
		}

		if (column.fieldname === "late_display") {
			if (data.late_entry) {
				return `<span class="bio-att-pill bio-att-pill--orange">${frappe.utils.escape_html(
					data.late_display || "Late"
				)}</span>`;
			}
			return `<span class="bio-att-muted">${frappe.utils.escape_html(
				data.late_display || "—"
			)}</span>`;
		}

		if (column.fieldname === "check_in_time" || column.fieldname === "check_out_time") {
			if (!data[column.fieldname] || data[column.fieldname] === "—") {
				return `<span class="bio-att-muted">—</span>`;
			}
			return `<span class="bio-att-time">${frappe.utils.escape_html(
				data[column.fieldname]
			)}</span>`;
		}

		if (column.fieldname === "lunch_display" || column.fieldname === "tea_display") {
			const text = data[column.fieldname] || "—";
			if (text === "—") {
				return `<span class="bio-att-muted">—</span>`;
			}
			const over = String(text).includes("Over Break");
			return `<span class="bio-att-break${over ? " bio-att-break--warn" : ""}">${frappe.utils.escape_html(
				text
			)}</span>`;
		}

		if (column.fieldname === "net_hours") {
			const hours = Number(data.net_hours || 0);
			const tone = hours >= 8 ? "green" : hours >= 4 ? "blue" : "orange";
			return `<span class="bio-att-hours bio-att-hours--${tone}">${hours.toFixed(2)}</span>`;
		}

		if (column.fieldname === "overtime_minutes") {
			const ot = Number(data.overtime_minutes || 0);
			if (!ot) {
				return `<span class="bio-att-muted">0</span>`;
			}
			return `<span class="bio-att-pill bio-att-pill--green">+${ot}m</span>`;
		}

		if (column.fieldname === "employee_name") {
			return `<span class="bio-att-name">${frappe.utils.escape_html(
				data.employee_name || ""
			)}</span>`;
		}

		return value;
	},

	onload(report) {
		if (!document.getElementById("bio-att-tracker-style")) {
			const style = document.createElement("style");
			style.id = "bio-att-tracker-style";
			style.textContent = `
				.bio-att-pill {
					display: inline-flex;
					align-items: center;
					padding: 2px 10px;
					border-radius: 999px;
					font-size: 12px;
					font-weight: 600;
					letter-spacing: 0.01em;
					line-height: 1.6;
					white-space: nowrap;
				}
				.bio-att-pill--green { background: #dcfce7; color: #166534; }
				.bio-att-pill--blue { background: #dbeafe; color: #1e40af; }
				.bio-att-pill--orange { background: #ffedd5; color: #9a3412; }
				.bio-att-pill--gray { background: #f1f5f9; color: #475569; }
				.bio-att-time {
					font-variant-numeric: tabular-nums;
					font-weight: 600;
					color: #0f172a;
				}
				.bio-att-break {
					font-variant-numeric: tabular-nums;
					color: #334155;
					font-size: 12px;
				}
				.bio-att-break--warn { color: #c2410c; font-weight: 600; }
				.bio-att-hours {
					font-variant-numeric: tabular-nums;
					font-weight: 700;
				}
				.bio-att-hours--green { color: #15803d; }
				.bio-att-hours--blue { color: #1d4ed8; }
				.bio-att-hours--orange { color: #c2410c; }
				.bio-att-name { font-weight: 600; color: #0f172a; }
				.bio-att-muted { color: #94a3b8; }
				.report-wrapper .dt-row .dt-cell {
					align-items: center;
				}
			`;
			document.head.appendChild(style);
		}

		report.page.add_inner_button(__("Open Attendance Day"), () => {
			frappe.set_route("List", "Biometric Attendance Day");
		});
	},
};
