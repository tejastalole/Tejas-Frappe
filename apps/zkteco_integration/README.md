# ZKTeco SenseFace 2A → Frappe / HRMS

ADMS push integration. Device punches create **Employee Checkin** records.

## Architecture

```
SenseFace 2A (192.168.1.201)
        │ ADMS
        ▼
http://192.168.1.10:8081/iclock/...
        │ Nginx (optional)
        ▼
Frappe (page_renderer) → zkteco_integration → Employee Checkin
```

## Your device settings (from the unit)

| Screen | Setting | Value |
|--------|---------|-------|
| Ethernet | IP Address | `192.168.1.201` |
| Ethernet | Gateway | `192.168.1.1` |
| Cloud Server | Server Mode | **ADMS** |
| Cloud Server | Server Address | `192.168.1.10` |
| Cloud Server | Server Port | `8081` |
| PC Connection | Device ID | `1` |
| PC Connection | TCP COMM. Port | `4370` |

## Install

```bash
bench --site site1.local install-app zkteco_integration
bench clear-cache
```

## Employee mapping

On each **Employee**, set **Attendance Device ID** = PIN registered on SenseFace.

## Optional Nginx on port 8081

```nginx
server {
    listen 8081;
    server_name 192.168.1.10;

    location /iclock {
        proxy_pass http://127.0.0.1:8007/iclock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Without Nginx, set device **Server Port** to `8007` (bench web port).

## Desk

- **ZKTeco Settings** – enable checkin creation, accept unknown devices
- **ZKTeco Device** – auto-created on first ADMS contact (by SN)
- **ZKTeco Punch Log** – raw punches + link to Employee Checkin

## Test

```bash
curl "http://127.0.0.1:8007/iclock/cdata?SN=TESTSN&options=all"
curl -X POST "http://127.0.0.1:8007/iclock/cdata?SN=TESTSN&table=ATTLOG" \
  -d $'1\t2026-08-06 09:00:00\t0\t1'
```
