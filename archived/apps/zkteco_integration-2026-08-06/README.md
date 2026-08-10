# ZKTeco Integration (ADMS Push)

Receives ZKTeco / SenseFace ADMS punches inside Frappe and creates **Employee Checkin** records.

## Architecture

```
SenseFace 2A
      │ ADMS
      ▼
http://YOUR_SERVER/iclock/...
      │
   Frappe (page_renderer)
      │
zkteco_integration
      │
Employee Checkin
```

## Install

```bash
bench --site site1.local install-app zkteco_integration
bench restart
```

## Device settings

| Field | Value |
|-------|-------|
| Server Mode | ADMS |
| Server Address | Your Frappe host / IP |
| Server Port | 80 / 443 (or site port) |

Firmware appends `/iclock/cdata` and `/iclock/getrequest` automatically.

## Employee mapping

Set **Attendance Device ID** on each Employee to match the PIN registered on the device.

## Optional Nginx (external ADMS port)

```nginx
location /iclock {
    proxy_pass http://127.0.0.1:8000/iclock;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Test endpoint

```
GET/POST /api/method/zkteco_integration.api.iclock
```

Returns plain `OK`.
