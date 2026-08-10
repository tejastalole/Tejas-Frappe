# Biometric Integration

ADMS / ZKTeco push + optional TCP pull for Frappe / ERPNext, tailored for devices like your **ZMM220_TFT** face/fingerprint terminal (`PT/BF/OFC/PM/01`).

```
Biometric Device (ADMS) ──HTTP push──► Frappe /iclock/* ──► Punch Log ──► Employee Checkin
         │                                      ▲
         └── optional TCP :4370 pull (pyzk) ────┘
```

## Your device (from firmware / Ethernet screens)

| Setting | Value |
|---------|--------|
| Label | PT/BF/OFC/PM/01 |
| IP | 192.168.1.183 |
| TCP COMM.Port | 4370 |
| MAC | 00:17:61:12:0c:cd |
| Platform | ZMM220_TFT |
| Firmware | 8.0.4.7-20230726 |
| Push Service | 2.0.33S (ADMS) |
| Cloud Server Mode | ADMS |
| Cloud Server Port (on device) | 8081 |
| Face / Finger | Face VX7.0 / Finger VX10.0 |

## Install

```bash
cd /path/to/bench
./env/bin/pip install -e apps/biometric_integration
bench pip install pyzk   # only needed for TCP pull
bench --site your-site install-app biometric_integration
```

## Configure the physical device (required for ADMS push)

On the terminal: **Cloud Server Setting**

1. Server Mode → **ADMS**
2. Server Address → your Frappe server IP or hostname (currently `0.0.0.0` on device — must change)
3. Server Port → **80** (HTTP) or **443** (HTTPS). Firmware appends `/iclock/cdata` etc.
4. Enable Domain Name → ON if using a hostname
5. Save / reboot if prompted

> Note: The device UI shows Server Port **8081**. That is the port the *device expects to talk to*. Point it at your Frappe site port (usually 80/443 behind nginx), not 4370.

## Configure ERPNext

1. Open **Biometric Integration** workspace → **Biometric Settings** (enable ADMS + Employee Checkin)
2. Open seeded **Biometric Device** `PT/BF/OFC/PM/01`
   - Replace Serial Number `PENDING-SN` with the real SN from Device Info (or let the first ADMS push rename it automatically)
3. On each Employee, set **Attendance Device ID** = biometric PIN / User ID
4. Install HRMS when ready so punches become **Employee Checkin** → Auto Attendance

## Optional: LAN pull (port 4370)

If ADMS cannot reach Frappe (NAT / firewall), enable **TCP Pull** in Settings and use **Test TCP Connection** / **Pull Attendance** on the device form. Requires `pyzk` and LAN reachability to `192.168.1.183:4370`.

## Endpoints (ADMS)

| Path | Purpose |
|------|---------|
| `/iclock/cdata` | Handshake + ATTLOG upload |
| `/iclock/getrequest` | Device polls for commands |
| `/iclock/devicecmd` | Command result ACK |
| `/iclock/registry` | Device registration |

Implemented via Frappe `page_renderer` (no special nginx rewrite required).

## Employee mapping

| Device PIN | ERPNext |
|------------|---------|
| `1` | Employee.attendance_device_id = `1` |

## Project layout

```
biometric_integration/
├── adms.py          # ADMS protocol
├── renderers.py     # /iclock page_renderer
├── sync.py          # Punch Log → Employee Checkin
├── zk_pull.py       # TCP 4370 via pyzk
├── api.py
├── scheduler.py
└── .../doctype/
    ├── biometric_settings/
    ├── biometric_device/
    ├── biometric_punch_log/
    └── biometric_sync_log/
```
