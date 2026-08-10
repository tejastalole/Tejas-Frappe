import frappe


def after_install():
	if not frappe.db.exists("Role", "Biometric Manager"):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Biometric Manager",
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)

	_seed_default_device()
	_seed_punch_status_mappings()

	if not frappe.db.exists("DocType", "Employee Checkin"):
		frappe.msgprint(
			"Biometric Integration: install HRMS for Employee Checkin / Auto Attendance.",
			alert=True,
		)


def _seed_default_device():
	"""Pre-fill device from on-site terminal PT/BF/OFC/PM/01 if none exist."""
	if frappe.db.count("Biometric Device"):
		return

	frappe.get_doc(
		{
			"doctype": "Biometric Device",
			"device_name": "PT/BF/OFC/PM/01",
			"serial_number": "PENDING-SN",
			"enabled": 1,
			"ip_address": "192.168.1.183",
			"tcp_port": 4370,
			"mac_address": "00:17:61:12:0c:cd",
			"platform": "ZMM220_TFT",
			"firmware_version": "8.0.4.7-20230726",
			"push_service": "2.0.33S-20220623",
			"face_algorithm": "Face VX7.0",
			"fingerprint_algorithm": "Finger VX10.0",
			"connection_mode": "ADMS Push",
			"notes": (
				"Cloud Server Setting on device: Server Mode=ADMS, Server Port=8081.\n"
				"Set Server Address to your Frappe host IP (currently 0.0.0.0 on device).\n"
				"Replace PENDING-SN with the real device Serial Number (System Info)."
			),
		}
	).insert(ignore_permissions=True)


def _seed_punch_status_mappings():
	"""Default device status codes → attendance event types."""
	settings = frappe.get_single("Biometric Settings")
	if settings.get("punch_status_mappings"):
		return

	defaults = [
		{"punch_status": "0", "event_category": "Check In Out", "log_type": "Check In"},
		{"punch_status": "1", "event_category": "Check In Out", "log_type": "Check Out"},
		{"punch_status": "2", "event_category": "Lunch Break", "log_type": "Break Start"},
		{"punch_status": "3", "event_category": "Lunch Break", "log_type": "Break End"},
		{"punch_status": "4", "event_category": "Tea Break", "log_type": "Break Start"},
		{"punch_status": "5", "event_category": "Tea Break", "log_type": "Break End"},
	]
	for row in defaults:
		settings.append("punch_status_mappings", row)

	settings.create_attendance_events = 1
	settings.save(ignore_permissions=True)
