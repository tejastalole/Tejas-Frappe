  # Biometric Integration — Cloud Deployment Guide

  Complete step-by-step guide to run **`biometric_integration`** on a **cloud / public server** so ZKTeco / eSSL / SenseFace devices push punches over the internet via ADMS (`/iclock/*`).

  This is different from a local WSL/LAN setup (`192.168.x.x:8007`). On cloud, the device must reach a **public hostname or public IP** on **port 80 or 443**.

  ---

  ## 1. Architecture (cloud)

  ```
  ┌─────────────────────┐         Internet          ┌──────────────────────────────┐
  │  Biometric Device   │  HTTPS/HTTP ADMS push     │  Cloud server (VPS / Frappe  │
  │  (SenseFace / F09)  │ ───────────────────────►  │  Cloud / self-hosted bench)  │
  │                     │  /iclock/cdata            │                              │
  │  Cloud Server:      │  /iclock/getrequest       │  Nginx → Gunicorn → Frappe   │
  │  host + port 80/443 │                           │  page_renderer → adms.py     │
  └─────────────────────┘                           │         ↓                    │
                                                    │  Biometric Punch Log → …     │
                                                    └──────────────────────────────┘
  ```

  | Item | Local (dev) | Cloud (production) |
  |------|-------------|-------------------|
  | Server address on device | PC LAN IP e.g. `192.168.10.30` | Public domain e.g. `erp.yourcompany.com` |
  | Port on device | `8007` (bench) | **`80`** (HTTP) or **`443`** (HTTPS) |
  | Path | Device appends `/iclock/...` | Same |
  | WSL / portproxy | Often required | **Not used** |
  | TLS | Usually none | **Strongly recommended (HTTPS)** |

  **Important:** Firmware appends `/iclock/cdata`, `/iclock/getrequest`, etc.  
  You configure only **host + port** on the device — **not** the full `/iclock` URL as “Server Address” (some UIs differ; see §7).

  ---

  ## 2. Choose a hosting option

  ### Option A — Frappe Cloud (managed)

  Best if you already use (or will use) [Frappe Cloud](https://frappecloud.com).

  1. Create a site (e.g. `yourcompany.frappe.cloud` or custom domain).
  2. Install apps: **ERPNext**, **HRMS** (recommended), then **`biometric_integration`**.
  3. Point a **custom domain** (optional but recommended for devices).
  4. SSL is handled by Frappe Cloud (use port **443** on the device).

  ### Option B — Self-hosted VPS (DigitalOcean, AWS, Azure, Contabo, etc.)

  1. Ubuntu 22.04 / 24.04 VPS with public IP.
  2. Install Frappe bench (production: Nginx + Supervisor + MariaDB + Redis).
  3. Create site with a real domain.
  4. Install `biometric_integration`.
  5. Open firewall ports **80** and **443**.

  ### Option C — On-prem server with public IP / VPN

  Same as B, but devices may reach the server via:

  - Public static IP + port forward (router), or  
  - Site-to-site VPN / WireGuard (device uses private IP of ERP).

  For pure internet ADMS, prefer **public HTTPS domain**.

  ---

  ## 3. Prerequisites

  ### Server

  - [ ] Frappe **v15+** (or your current compatible version)
  - [ ] Apps: `frappe`, `erpnext`, `biometric_integration`
  - [ ] Recommended: `hrms` (for Employee Checkin / Attendance)
  - [ ] Site timezone: **`Asia/Kolkata`** (or your country)
  - [ ] Production stack: **Nginx + Gunicorn** (not only `bench start`)
  - [ ] Valid DNS A/AAAA record for the site hostname
  - [ ] SSL certificate (Let’s Encrypt / Frappe Cloud / Cloudflare)

  ### Network

  - [ ] Device has working internet (Ethernet/Wi‑Fi)
  - [ ] Outbound HTTPS/HTTP from device to your server is allowed
  - [ ] No captive portal blocking the device
  - [ ] Corporate firewall allows device → TCP **443** (or 80) to your host

  ### Device

  - [ ] ZKTeco / eSSL / SenseFace with **ADMS / Cloud Server** support
  - [ ] Known **Serial Number (SN)** (System Info)
  - [ ] Users enrolled with PIN = Employee **Attendance Device ID**

  ---

  ## 4. Install the app on the cloud site

  ### 4.1 Get the app code onto the bench

  On the server (SSH), as the frappe user:

  ```bash
  cd /path/to/frappe-bench

  # If app is in a private Git repo:
  bench get-app biometric_integration https://YOUR_GIT_HOST/YOUR_ORG/biometric_integration.git

  # Or copy/rsync the app folder into apps/biometric_integration
  ```

  ### 4.2 Install on the site

  ```bash
  bench --site YOUR_SITE_NAME install-app biometric_integration
  bench --site YOUR_SITE_NAME migrate
  bench --site YOUR_SITE_NAME clear-cache
  bench build --app biometric_integration
  ```

  Replace `YOUR_SITE_NAME` with e.g. `erp.yourcompany.com` or `site1.local` (production should use a real domain).

  ### 4.3 Restart production processes

  ```bash
  bench restart
  # or
  sudo supervisorctl restart all
  sudo systemctl reload nginx
  ```

  ### 4.4 Verify Desk

  Open:

  ```
  https://YOUR_DOMAIN/app/biometric-integration
  ```

  You should see the **Biometric Integration** workspace (devices, punch logs, settings, attendance report).

  ---

  ## 5. DNS and SSL (critical for devices)

  ### 5.1 DNS

  Create an **A record**:

  | Type | Host | Value |
  |------|------|--------|
  | A | `erp` (or `@`) | Your VPS public IP |

  Example result: `erp.yourcompany.com` → `203.0.113.10`

  Wait for DNS propagation (`ping erp.yourcompany.com`).

  ### 5.2 SSL (Let’s Encrypt example)

  On a standard bench production install:

  ```bash
  cd /path/to/frappe-bench
  bench setup nginx
  sudo bench setup lets-encrypt YOUR_SITE_NAME
  # or your org’s usual cert process
  ```

  Frappe Cloud: enable SSL / custom domain in the dashboard.

  ### 5.3 Why HTTPS matters

  - Many networks block plain HTTP.
  - Device firmware is more reliable with a stable domain + 443.
  - Avoids mixed content / MITM on attendance data.

  **Device port when using HTTPS:** usually **`443`**.  
  **Device port when using HTTP only:** **`80`**.

  Do **not** put `8000` / `8007` on the device for production — those are development bench ports behind Nginx.

  ---

  ## 6. Nginx / Host header requirements

  ADMS requests must hit the **correct Frappe site**.

  ### 6.1 Multi-site benches

  If one bench hosts multiple sites, Nginx uses the **Host** header to pick the site.

  Devices often send:

  ```http
  Host: erp.yourcompany.com
  ```

  or sometimes only the IP. Best practice:

  1. Give the site a **real domain** in `sites/YOUR_SITE/site_config.json`:

  ```json
  {
    "host_name": "https://erp.yourcompany.com"
  }
  ```

  2. Ensure Nginx `server_name` includes that domain.
  3. Prefer configuring the **device with the domain name**, not the raw IP (unless you have a single default site and `dns_multitenant` / default site is set).

  ### 6.2 Single-site / default site

  In `sites/common_site_config.json` or site config:

  ```json
  {
    "default_site": "erp.yourcompany.com"
  }
  ```

  Or:

  ```bash
  bench use erp.yourcompany.com
  ```

  So even if the device hits by IP, traffic still lands on that site (only safe with **one** production site).

  ### 6.3 Confirm `/iclock` is not blocked

  `biometric_integration` registers a **page_renderer** for paths starting with `iclock`.  
  Nginx should **proxy all paths** to Frappe (standard bench Nginx config already does).

  You should **not** need a special rewrite for `/iclock` if using normal Frappe Nginx.

  Test from any PC:

  ```bash
  curl -i "https://erp.yourcompany.com/iclock"
  # Expect body: OK

  curl -i "https://erp.yourcompany.com/iclock/getrequest?SN=YOUR_SERIAL"
  # Expect body: OK

  curl -i "https://erp.yourcompany.com/iclock/cdata?SN=YOUR_SERIAL&options=all"
  # Expect handshake text starting with: GET OPTION FROM: YOUR_SERIAL
  ```

  If these fail from the internet, the device cannot work.

  ---

  ## 7. Configure the biometric device (Cloud Server / ADMS)

  Menu names vary by firmware (Cloud Server / ADMS / Push / Communication).

  ### 7.1 Recommended settings

  | Setting | Value |
  |---------|--------|
  | **Server Mode** | **ADMS** (or Cloud Server / Push) |
  | **Server Address** | `erp.yourcompany.com` (domain) **or** public IP |
  | **Server Port** | **`443`** if HTTPS, **`80`** if HTTP |
  | **Enable Domain Name** | **ON** when using a hostname |
  | **HTTPS / SSL** | ON if your device firmware supports it and you use 443 |
  | **Realtime** | **ON** (push punches immediately) |
  | **Only one server** | Do not leave an old eSSL / other cloud URL active |

  ### 7.2 What the device actually calls

  With address `erp.yourcompany.com` and port `443`, the device will call roughly:

  ```
  https://erp.yourcompany.com/iclock/cdata?...
  https://erp.yourcompany.com/iclock/getrequest?SN=...
  ```

  You do **not** type `/iclock` in Server Address on most firmwares.

  ### 7.3 Serial number

  Note the device **SN** (e.g. `NYU7254601554`).  
  In ERP: **Biometric Device** → Serial Number must match exactly.

  ### 7.4 Date / Time / Timezone on device

  - Set **correct date & time**
  - Use **IST (UTC+5:30)** for India — **not UTC+5:00**
  - Prefer NTP if available (`pool.ntp.org` / `time.google.com`)
  - This app’s ADMS handshake does **not** force a `TimeZone=` value (avoids SenseFace overwriting 5:30 → 5:00)

  ### 7.5 After saving cloud settings

  1. Save / Apply on device  
  2. Reboot device once  
  3. Wait 30–60 seconds  
  4. In ERP open **Biometric Device** → check **Last Seen** updates  

  If **Last Seen** is live, ADMS connectivity works.

  ---

  ## 8. Configure ERP (Biometric Integration)

  ### 8.1 Biometric Settings

  Open **Biometric Settings**:

  | Field | Recommended (cloud) |
  |-------|---------------------|
  | Enabled | Yes |
  | Accept Unknown Devices | Yes (first connect) or No (strict) |
  | Create Attendance Events | Yes |
  | Create Employee Checkin | Yes (if HRMS installed) |
  | Use Time-Based Punch Routing | Yes |
  | Office Start | `09:00:00` |
  | Late Entry After | `10:00:00` |
  | Office End / Check Out After | `19:00:00` |
  | Lunch window | `12:00:00` – `15:00:00` |
  | Tea window | `16:00:00` – `18:00:00` |
  | Enable TCP Pull | **No** for SenseFace on cloud (use ADMS Push) |

  TCP Pull (`pyzk` / port 4370) needs LAN reachability to the device. On cloud, devices almost never expose 4370 publicly — **use ADMS Push only**.

  ### 8.2 Biometric Device

  Create / update device:

  | Field | Value |
  |-------|--------|
  | Device Name | e.g. Office Reception |
  | Serial Number | Exact SN from device |
  | Enabled | Yes |
  | Connection Mode | **ADMS Push** |
  | IP Address | Optional (LAN IP of device; not required for ADMS) |

  ### 8.3 Employees

  For each employee:

  1. Open **Employee**
  2. Set **Attendance Device ID** = PIN / User ID on the biometric machine  
  3. Status = Active  

  Mismatch → Punch Log may still save, but employee link / events can fail.

  ### 8.4 Report

  Use **Employee Attendance Tracker**:

  ```
  https://YOUR_DOMAIN/app/query-report/Employee%20Attendance%20Tracker
  ```

  ---

  ## 9. End-to-end test checklist (cloud)

  ### Step 1 — Server health

  ```bash
  curl -s "https://YOUR_DOMAIN/iclock"
  # OK
  ```

  ### Step 2 — Device online

  - Punch is not required yet  
  - **Biometric Device → Last Seen** should refresh every ~30 seconds  

  Server logs (optional):

  ```bash
  # self-hosted
  sudo tail -f /var/log/nginx/access.log | grep iclock
  # or bench logs / journalctl for gunicorn
  ```

  You want lines like:

  ```
  GET /iclock/getrequest?SN=YOUR_SERIAL
  ```

  ### Step 3 — Punch once

  1. Employee punches on device  
  2. Within ~30 seconds look for:

  ```
  POST /iclock/cdata?SN=...&table=ATTLOG
  ```

  3. Open **Biometric Punch Log** — new row appears  
  4. If Accepted → row also in Check In Check Out / Lunch / Tea per time windows  

  ### Step 4 — Verify routing windows (defaults)

  | Time | DocType |
  |------|---------|
  | ~9:00–10:00 AM | Check In Check Out → Check In |
  | 12:00–3:00 PM | Lunch Break |
  | 4:00–6:00 PM | Tea Break |
  | After 7:00 PM | Check In Check Out → Check Out |

  ---

  ## 10. Frappe Cloud–specific notes

  1. **Install app** from marketplace or private bench (as allowed by your plan).  
  2. **Custom domain** strongly recommended for devices.  
  3. Device settings:

    - Server Address = your custom domain or `xxx.frappe.cloud`  
    - Port = **443**  
    - Domain Name = ON  

  4. Confirm `/iclock` from outside:

    ```bash
    curl -s "https://your-site.frappe.cloud/iclock"
    ```

  5. If `/iclock` returns HTML login / 404 instead of `OK`, the app is not installed on that site or renderer is not loaded — reinstall/migrate/clear-cache.

  6. Frappe Cloud sites are multi-tenant: **always use the site hostname**, not a shared IP without Host header.

  ---

  ## 11. Self-hosted VPS — minimal production outline

  ```bash
  # 1) Bench already exists with site erp.yourcompany.com
  cd ~/frappe-bench

  # 2) App
  bench get-app biometric_integration <REPO_URL>
  bench --site erp.yourcompany.com install-app biometric_integration
  bench --site erp.yourcompany.com migrate
  bench build --app biometric_integration
  bench restart

  # 3) Firewall (UFW example)
  sudo ufw allow 22/tcp
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw enable

  # 4) Confirm
  curl -s https://erp.yourcompany.com/iclock
  ```

  Open cloud security group / firewall for **80** and **443** only (do not expose MariaDB 3306 or Redis).

  ---

  ## 12. Security recommendations

  | Topic | Recommendation |
  |-------|----------------|
  | Transport | Prefer **HTTPS / 443** |
  | Unknown devices | After first setup, turn **Accept Unknown Devices = No** |
  | Roles | Restrict Desk to **System Manager / Biometric Manager / HR** |
  | Backups | Daily site backup (`bench backup`) |
  | Updates | Update `biometric_integration` via git + `bench migrate` |
  | Device password | Change default admin PIN on the biometric machine |
  | Public IP | Prefer domain + SSL over raw IP |
  | TCP 4370 | Do **not** open 4370 to the internet |

  This ADMS endpoint is intentionally open (no ERP login) — that is how ZKTeco push works. Protect it with HTTPS and by not advertising unused ports.

  ---

  ## 13. Troubleshooting (cloud)

  ### A) Punch Log empty, Last Seen empty

  | Check | Action |
  |-------|--------|
  | DNS | `ping YOUR_DOMAIN` from office network |
  | Port | Device port 443/80 matches SSL setup |
  | curl `/iclock` | Must return `OK` from outside office |
  | Firewall | Allow inbound 80/443 on VPS |
  | Wrong site | Multi-site Host header / default_site |
  | Old cloud URL | Remove eSSL / other ADMS server from device |

  ### B) Last Seen updates, but no Punch Log

  | Check | Action |
  |-------|--------|
  | Only `getrequest`, no `cdata` ATTLOG | Punch again; enable Realtime; force upload on device |
  | Stamp already sent | Device won’t re-send old punches after you delete Punch Logs in ERP |
  | Wrong SN | Serial on Biometric Device must match |

  ### C) Punch Log exists, status Rejected

  Open **Rejection Reason** on Punch Log:

  - Outside time window  
  - Already checked in  
  - Duplicate within tolerance  

  Windows are controlled in **Biometric Settings**, not by cloud networking.

  ### D) Times are 30 minutes wrong

  - Device timezone must be **IST (+5:30)**, not +5:00  
  - Site timezone **Asia/Kolkata**  
  - App stores punch time **as sent by device**

  ### E) Works on LAN laptop `curl` but not from device

  - Device DNS failure → try IP temporarily (single-site only)  
  - Device HTTP vs HTTPS mismatch  
  - SIM/Wi‑Fi APN blocking non-standard ports (use 443)  

  ### F) Browser shows Frappe login on `/iclock`

  App not active / wrong site / cache:

  ```bash
  bench --site YOUR_SITE install-app biometric_integration
  bench --site YOUR_SITE migrate
  bench --site YOUR_SITE clear-cache
  bench restart
  ```

  ---

  ## 14. What you do **not** need on cloud

  | Item | Why |
  |------|-----|
  | WSL portproxy | Only for local Windows + WSL |
  | Device pointing to `127.0.0.1` | Loopback is the device itself |
  | Port `8007` on device | Dev only; production uses Nginx 80/443 |
  | eTimeTrackLite middle server | This app **is** the ADMS server |
  | Public TCP 4370 / pyzk pull | Use ADMS Push |

  ---

  ## 15. Production go-live checklist

  - [ ] Site live on HTTPS domain  
  - [ ] `curl https://DOMAIN/iclock` → `OK`  
  - [ ] `biometric_integration` installed & migrated  
  - [ ] Biometric Settings saved (ADMS Push, office policy)  
  - [ ] Biometric Device created with correct SN  
  - [ ] Employees have Attendance Device ID = PIN  
  - [ ] Device Cloud Server = domain, port 443, ADMS, Realtime ON  
  - [ ] Device time = correct IST  
  - [ ] Last Seen updating  
  - [ ] Test punch → Punch Log → correct event DocType  
  - [ ] Employee Attendance Tracker report checked  
  - [ ] Accept Unknown Devices disabled (optional harden)  
  - [ ] Backups scheduled  

  ---

  ## 16. Quick reference — device vs ERP

  | Layer | Value |
  |-------|--------|
  | Device Server Address | `erp.yourcompany.com` |
  | Device Server Port | `443` |
  | Device Mode | ADMS |
  | ERP endpoint | `/iclock/*` (automatic) |
  | First proof of life | Biometric Device **Last Seen** |
  | First proof of punch | Biometric Punch Log row |
  | Daily review | Employee Attendance Tracker report |

  ---

  ## 17. Related docs

  | File | Purpose |
  |------|---------|
  | `IMPLEMENT.readme.md` | Full product / attendance rules (windows, DocTypes, state engine) |
  | `README.md` | App overview |
  | This file (`CLOUDREADME.md`) | **Cloud / public deployment only** |

  ---

  ## 18. Support commands (self-hosted)

  ```bash
  # App status
  bench --site YOUR_SITE list-apps

  # Reinstall hooks / clear
  bench --site YOUR_SITE clear-cache
  bench restart

  # Count punch logs
  bench --site YOUR_SITE mariadb -e "SELECT COUNT(*) FROM \`tabBiometric Punch Log\`;"

  # Device last seen
  bench --site YOUR_SITE mariadb -e "SELECT name, serial_number, last_seen, last_sync FROM \`tabBiometric Device\`;"
  ```

  ---

  **Bottom line:** On cloud, point the biometric **Cloud Server** to your **public HTTPS domain on port 443**, install `biometric_integration` on that site, and confirm `/iclock` returns `OK` from the internet. When **Last Seen** updates and ATTLOG posts appear, punches will land in **Biometric Punch Log** the same way as on local bench — without WSL or port `8007`.
