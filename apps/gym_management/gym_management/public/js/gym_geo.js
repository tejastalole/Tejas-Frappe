frappe.provide("gym_management.geo");

gym_management.geo.get_location = function (callback) {
	if (!navigator.geolocation) {
		callback(null);
		return;
	}

	navigator.geolocation.getCurrentPosition(
		(pos) =>
			callback({
				latitude: pos.coords.latitude,
				longitude: pos.coords.longitude,
			}),
		() => callback(null),
		{ enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
	);
};

gym_management.geo.with_location = function (run) {
	gym_management.geo.get_location((coords) => {
		const args = coords
			? { latitude: coords.latitude, longitude: coords.longitude }
			: {};
		if (!coords) {
			frappe.show_alert({
				message: __("Location not available — check-in saved without GPS."),
				indicator: "orange",
			});
		}
		run(args);
	});
};
