(() => {
	const apply = () => {
		const route = (frappe.get_route_str && frappe.get_route_str()) || "";
		const is_etp_workspace =
			route === "Workspaces/Easy TimePro" ||
			route === "Workspaces/easy-timepro";

		// Never keep theme class on list/form pages
		if (!is_etp_workspace) {
			document.body.classList.remove("etp-glass-workspace");
			return;
		}
		document.body.classList.add("etp-glass-workspace");
	};

	$(document).on("page-change", apply);
	frappe.after_ajax && frappe.after_ajax(apply);
	$(apply);
})();
