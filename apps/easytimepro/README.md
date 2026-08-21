# Easy TimePro Integration

Pull biometric check-in / check-out data from **ZKTeco Easy TimePro** into Frappe.

## Flow

```text
Biometric Device → Easy TimePro (http://192.168.10.30:8082)
                              ↓
           Frappe auto-sync (Sync Interval in Seconds, default 5s)
                              ↓
              Easy TimePro Punch Log (+ optional Employee Checkin)
```

## Setup

1. Install app and open workspace **Easy TimePro**
2. Open **Easy TimePro Settings**
   - Base URL: `http://192.168.10.30:8082`
   - Username / Password
   - Enable Sync
   - **Sync Interval (Seconds)** — how often Frappe pulls punches (default **5**, minimum 5)
3. Click **Test Connection**, then **Sync Now**
4. View punches in **Easy TimePro Punch Log**

## Employee mapping

Easy TimePro **Employee ID** (`emp_code`) is stored on Frappe Employee as **Attendance Device ID**.

Example: Easy TimePro Employee ID `1` (Tejas) → Employee.attendance_device_id = `1`

In **Easy TimePro Settings**, use **Sync Employee IDs** to match names from Easy TimePro and fix device IDs automatically.

## Install

```bash
bench --site your-site install-app easytimepro
bench --site your-site migrate
```
