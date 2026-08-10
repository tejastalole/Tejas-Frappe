frappe.provide("biometric_integration");

(function () {
	function patch_links_widget() {
		if (biometric_integration.links_widget_patched) {
			return;
		}

		const LinksWidget = frappe.widget?.widget_factory?.links;
		if (!LinksWidget) {
			return;
		}

		const original_set_body = LinksWidget.prototype.set_body;
		LinksWidget.prototype.set_body = function () {
			original_set_body.call(this);
			this.links.forEach((item, idx) => {
				if (item.link_type !== "DocType" || item.record_count == null) {
					return;
				}

				const $link = this.link_list[idx];
				if (!$link || $link.find(".link-record-count").length) {
					return;
				}

				$link.find(".link-content").append(
					`<span class="indicator-pill no-indicator-dot ellipsis gray link-record-count ml-2">${item.record_count}</span>`
				);
			});
		};

		biometric_integration.links_widget_patched = true;
	}

	function try_patch() {
		patch_links_widget();
		if (!biometric_integration.links_widget_patched) {
			setTimeout(try_patch, 200);
		}
	}

	$(document).on("app_ready", try_patch);
	frappe.ready(try_patch);
})();
