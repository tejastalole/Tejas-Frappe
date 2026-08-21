// Hide ID (name) column/filter on Employee Checkin without overriding HRMS list behaviour.
frappe.listview_settings["Employee Checkin"] = frappe.listview_settings["Employee Checkin"] || {};
frappe.listview_settings["Employee Checkin"].hide_name_column = true;
frappe.listview_settings["Employee Checkin"].hide_name_filter = true;
