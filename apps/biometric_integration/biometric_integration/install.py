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
	ensure_attendance_tracker_workspace()

	if not frappe.db.exists("DocType", "Employee Checkin"):
		frappe.msgprint(
			"Biometric Integration: install HRMS for Employee Checkin / Auto Attendance.",
			alert=True,
		)


def after_migrate():
	ensure_attendance_tracker_workspace()


def ensure_attendance_tracker_workspace():
	"""Add Employee Attendance Tracker report to Biometric workspace."""
	if not frappe.db.exists("Workspace", "Biometric Integration"):
		return

	ws = frappe.get_doc("Workspace", "Biometric Integration")
	changed = False

	has_link = any(
		(row.link_type == "Report" and row.link_to == "Employee Attendance Tracker")
		for row in (ws.links or [])
	)
	if not has_link:
		ws.append(
			"links",
			{
				"type": "Link",
				"label": "Employee Attendance Tracker",
				"link_type": "Report",
				"link_to": "Employee Attendance Tracker",
				"report_ref_doctype": "Biometric Attendance Day",
				"is_query_report": 1,
				"onboard": 0,
			},
		)
		changed = True

	has_shortcut = any(
		(row.label == "Attendance Tracker" or row.link_to == "Employee Attendance Tracker")
		for row in (ws.shortcuts or [])
	)
	if not has_shortcut:
		ws.append(
			"shortcuts",
			{
				"label": "Attendance Tracker",
				"type": "Report",
				"link_to": "Employee Attendance Tracker",
				"report_ref_doctype": "Biometric Attendance Day",
				"color": "Blue",
			},
		)
		changed = True
		# Place shortcut in Quick Access block of workspace content
		try:
			import json

			content = json.loads(ws.content or "[]")
			exists = any(
				block.get("type") == "shortcut"
				and (block.get("data") or {}).get("shortcut_name") == "Attendance Tracker"
				for block in content
			)
			if not exists:
				# Insert after Quick Access header if present
				insert_at = len(content)
				for idx, block in enumerate(content):
					if block.get("id") == "sc_employee":
						insert_at = idx + 1
						break
				content.insert(
					insert_at,
					{
						"id": "sc_att_tracker",
						"type": "shortcut",
						"data": {"shortcut_name": "Attendance Tracker", "col": 3},
					},
				)
				ws.content = json.dumps(content)
		except Exception:
			pass

	if changed:
		ws.save(ignore_permissions=True)
		frappe.db.commit()


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
