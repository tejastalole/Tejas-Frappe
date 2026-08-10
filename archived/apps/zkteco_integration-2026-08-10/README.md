# Exacuer Biometric (`zkteco_integration`)

Production ZKTeco → ERPNext attendance integration for **ERPNext Cloud**.

## Architecture

```
ZKTeco F09 (192.168.1.201:4370)
        │  pyzk (LAN only)
        ▼
Local Sync Agent  (Windows / Linux PC on same LAN)
        │  HTTPS + API Key
        ▼
https://erp.exacuer.com
        │
zkteco_integration (Frappe)
        ▼
Employee Checkin
```

**Cloud never dials private device IPs.** Port 4370 stays inside the LAN.

Timezone: **Asia/Kolkata**

---

## 1. Install Frappe app (Cloud / Bench)

```bash
# If developing from this repo:
bench get-app /path/to/zkteco_integration
# or
bench get-app https://your-git/zkteco_integration

bench --site erp.exacuer.com install-app zkteco_integration
bench --site erp.exacuer.com migrate
bench restart
```

Dependencies (optional on-prem LAN desk sync):

```bash
bench pip install pyzk
```

---

## 2. Create API credentials (not Administrator password)

1. Desk → **User** → create dedicated user e.g. `zkteco-agent@exacuer.com`
2. Roles: **System Manager** or a custom role with rights to Employee Checkin / ZKTeco DocTypes
3. User → **API Access** → Generate **API Key** + **API Secret**
4. Copy into local agent `config.json` (never commit secrets)

---

## 3. Desk setup

1. Open workspace **Exacuer Biometric**
2. **ZKTeco Settings** → enable, Auto Detect IN/OUT
3. **ZKTeco Device** → create device:
   - Device Name: `NYU7254601554` (used as `device_id`)
   - IP: `192.168.1.201` (for documentation / on-prem Test Connection)
   - Port: `4370`
4. **ZKTeco Employee Mapping**:
   - ZKTeco User ID `1001` → Employee `HR-EMP-00001`

Desk **Test Connection / Sync Now** only work if the Frappe site itself is on the same LAN. On ERPNext Cloud, use the **local agent**.

---

## 4. Local Sync Agent

Path: `zkteco_sync_agent/`

### Windows

```bat
cd zkteco_sync_agent
copy config.example.json config.json
REM edit config.json — erp_url, api_key, api_secret, devices
start_agent.bat
```

### Linux

```bash
cd zkteco_sync_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
# edit config.json
python agent.py --config config.json
```

### config.json

```json
{
  "erp_url": "https://erp.exacuer.com",
  "api_key": "YOUR_API_KEY",
  "api_secret": "YOUR_API_SECRET",
  "timezone": "Asia/Kolkata",
  "sync_interval": 60,
  "devices": [
    {"name": "NYU7254601554", "ip": "192.168.1.201", "port": 4370}
  ]
}
```

### Windows service (NSSM)

See `service.example.ini`. Install with [NSSM](https://nssm.cc/) so the agent starts on reboot without an open terminal.

---

## 5. Cloud APIs

All require: `Authorization: token API_KEY:API_SECRET`

| Method | Purpose |
|--------|---------|
| `zkteco_integration.api.create_employee_checkin` | Single punch |
| `zkteco_integration.api.bulk_create_employee_checkins` | Bulk punches |
| `zkteco_integration.api.sync_attendance` | Alias for bulk |
| `zkteco_integration.api.device_heartbeat` | Online/Offline status |
| `zkteco_integration.api.get_device_config` | Mappings / stamps |
| `zkteco_integration.api.dashboard_stats` | Desk stats |

### Bulk example

```bash
curl -X POST "https://erp.exacuer.com/api/method/zkteco_integration.api.bulk_create_employee_checkins" \
  -H "Authorization: token KEY:SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "NYU7254601554",
    "records": [
      {"zkteco_user_id": "1001", "timestamp": "2026-08-10 09:57:05", "log_type": "IN"}
    ]
  }'
```

Duplicate detection: **employee + time + device_id**

---

## 6. Offline / failures

- Cloud down → agent stores punches in local **SQLite** (`data/attendance_queue.db`) and retries
- Device down → exponential backoff (5/10/30/60s), heartbeat Offline
- Missing mapping → record fails with clear error in Sync Log

---

## 7. Security

- HTTPS only to cloud
- Never expose TCP 4370 publicly
- Never log API secrets
- Never put secrets in git (`config.json` is local only; use `config.example.json`)

---

## 8. Multiple devices

Add multiple entries under `devices` in `config.json`. Each has independent sync stamp and status.
