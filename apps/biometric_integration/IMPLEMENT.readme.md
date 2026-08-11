# Biometric Integration — Full Implementation Guide

Plain-English guide for the **current** `biometric_integration` app on Frappe / ERPNext v15.

This document matches what is implemented today: ADMS push, attendance state engine, lunch/tea windows, daily summary, HRMS Employee Checkin (optional), workspace, and regularization.

---

## 1. What this app does (end-to-end)

1. Employee puts face / finger on the biometric machine (e.g. ZKTeco SenseFace 2A).
2. Machine **pushes** the punch to your Frappe server over ADMS (`/iclock/*`).
3. App **always** saves the raw punch in **Biometric Punch Log** (audit trail).
4. App maps the device punch status code using **Biometric Settings → Punch Status Mappings**.
5. App validates the punch with the **attendance state engine** (sequence, duplicates, lunch/tea time windows).
6. If valid, app creates one event in the correct DocType:
   - **Biometric Check In Check Out** — Regular Check In / Check Out
   - **Biometric Lunch Break** — Break Start / Break End
   - **Biometric Tea Break** — Break Start / Break End
7. App refreshes **Biometric Attendance Day** (late, early exit, overtime, break excess, net hours, current state).
8. Optionally creates HRMS **Employee Checkin** for Regular Check In / Check Out only (not for lunch/tea).

```
ZKTeco device (ADMS)
        │
        ▼
   /iclock/*  (Frappe page_renderer)
        │
        ▼
 Biometric Punch Log  ←── always saved (Accepted / Rejected / Duplicate)
        │
        ▼
 Attendance State Engine
   • resolve status → category + log type
   • duplicate tolerance
   • state rules (NOT_STARTED → … → COMPLETED)
   • lunch window 12:00–15:00
   • tea window 16:00–18:00
        │
        ├──────────────┬──────────────┐
        ▼              ▼              ▼
 Check In Check Out  Lunch Break   Tea Break
        │
        ▼
 Biometric Attendance Day (daily summary)
        │
        ▼ (optional, Regular In/Out only)
 Employee Checkin → HRMS Auto Attendance
```

**Important:** This app does **not** replace HRMS Shift Type / Shift Assignment.  
Biometric Settings office hours (09:00–18:00) drive **biometric late/overtime/break rules**.  
HRMS **Off-Shift / On-Shift** on Employee Checkin needs a separate **Shift Type** + assignment.

---

## 2. DocTypes used (no duplicates of the three event types)

| DocType | Purpose |
|---------|---------|
| **Biometric Settings** | Enable ADMS, mappings, office policy, lunch/tea windows, TCP pull options |
| **Biometric Device** | Device master (serial, IP, ADMS/TCP mode, last seen) |
| **Biometric Punch Log** | Raw punch audit trail + processing status |
| **Biometric Check In Check Out** | Regular Check In / Check Out events |
| **Biometric Lunch Break** | Lunch Break Start / End |
| **Biometric Tea Break** | Tea Break Start / End |
| **Biometric Attendance Day** | One row per employee per date — daily summary |
| **Biometric Attendance Regularization** | Admin correction for forgotten punches |
| **Biometric Sync Log** | TCP pull / sync errors |
| **Biometric Punch Status Mapping** | Child table on Settings (status code → event) |
| **Employee Checkin** (HRMS) | Optional, Regular In/Out only |
| **Employee** | Must have **Attendance Device ID** = machine PIN |

---

## 3. Office policy (current defaults)

Configure in **Biometric Settings → Office Policy**:

| Rule | Default | Used for |
|------|---------|----------|
| Office Start | **09:00 AM** | Check-in window start |
| Late Entry After | **10:00 AM** | Late minutes count only after this time |
| Office End | **06:00 PM** | Early exit / overtime |
| Lunch window | **12:00 PM – 3:00 PM** | Lunch Start **and** Lunch End must be inside this window |
| Lunch duration | **45 minutes** | Expected break end = Lunch Start + 45 min |
| Tea window | **4:00 PM – 6:00 PM** | Tea Start **and** Tea End must be inside this window |
| Tea duration | **15 minutes** | Expected break end = Tea Start + 15 min |
| Duplicate punch tolerance | **120 seconds** | Same category/log type within window → Duplicate |
| Allow Checkout With Incomplete Break | No | If Yes, Check Out allowed even if break end missing |

### Lunch (check in / check out of lunch)

- **Lunch Break Start** = lunch check-in  
- **Lunch Break End** = lunch check-out  
- Both punches must be between **12:00 PM and 3:00 PM**.  
- Outside window → **Rejected** (Punch Log still kept).

Valid example:

| Time | Event |
|------|--------|
| 1:00 PM | Lunch Break Start |
| 1:45 PM | Lunch Break End (on time) |
| 1:52 PM | Lunch Break End (accepted if still ≤ 3:00 PM; **Over Break** + 7 min excess) |

Rejected example:

| Time | Why |
|------|-----|
| 11:30 AM Lunch Start | Before 12:00 PM |
| 3:15 PM Lunch End | After 3:00 PM |

### Tea (check in / check out of tea)

- **Tea Break Start** / **Tea Break End** must be between **4:00 PM and 6:00 PM**.

Valid example: 4:00 PM Start → 4:15 PM End.  
Rejected example: 3:30 PM Tea Start.

### Break duration vs window

- **Duration** (45 / 15) = expected length from Break Start.  
- **Window** = clock range when break punches are allowed.  
- Late return inside the window is **accepted**; excess minutes go to Attendance Day as **Over Break**.

---

## 4. Punch routing (time-based — current default)

**Use Time-Based Punch Routing** is enabled by default in **Biometric Settings**.

Device punch status codes are **ignored for routing**. Punch type is decided only by **clock time**:

| Punch time | Routed to | DocType / Log Type |
|------------|-----------|--------------------|
| **Before 9:00 AM** (before Office Start) | Regular **Check In** | Biometric Check In Check Out → Check In |
| **9:00 AM – 10:00 AM** | Regular **Check In** (on time) | No late minutes |
| **After 10:00 AM** (before lunch, not yet checked in) | Regular **Check In** (late) | Late minutes = punch time − 10:00 AM |
| **12:00 PM – 3:00 PM** | Lunch **check in** then **check out** | First punch → Break Start; next → Break End |
| **4:00 PM – 6:00 PM** | Tea **check in** then **check out** | First punch → Break Start; next → Break End |
| **After 6:00 PM** (after Office End) | Regular **Check Out** | Biometric Check In Check Out → Check Out |

Gaps (already checked in):

| Gap | Result |
|-----|--------|
| 9:00 AM – 12:00 PM (already checked in) | Rejected |
| 3:00 PM – 4:00 PM | Rejected |

Within lunch/tea windows the **first** punch is Break Start (check in to break) and the **second** is Break End (check out from break).

Lunch and Tea punches are **always stored** in **Biometric Lunch Break** / **Biometric Tea Break** even if Regular Check In is missing for that day.

Regular **Check In** (before office start / late before lunch) and **Check Out** (after office end) are **always stored** in **Biometric Check In Check Out**. Check Out is saved even if Check In is missing.

### Punch Status Mapping (fallback only)

If **Use Time-Based Punch Routing** is turned **Off**, device status codes are used again:

| Device punch status | Event category | Log type |
|---------------------|----------------|----------|
| `0` | Check In Out | Check In |
| `1` | Check In Out | Check Out |
| `2` | Lunch Break | Break Start |
| `3` | Lunch Break | Break End |
| `4` | Tea Break | Break Start |
| `5` | Tea Break | Break End |

Change mappings only when time-based routing is disabled.

---

## 5. Attendance states (state machine)

Before creating an event, the engine loads that employee’s day context and computes **current state**:

| State | Meaning | Allowed next punches |
|-------|---------|----------------------|
| **NOT_STARTED** | No Check In yet | Check In only |
| **WORKING** | Checked in, not on break | Lunch Start, Tea Start, Check Out |
| **LUNCH_BREAK** | Lunch Start done, End missing | Lunch Break End only |
| **TEA_BREAK** | Tea Start done, End missing | Tea Break End only |
| **COMPLETED** | Check Out done | Nothing |
| **INCOMPLETE** | Missing break end (or similar gap) | Depends on flags / remaining events |

### Punch Log processing status

| Status | Meaning |
|--------|---------|
| **Pending** | Not processed yet |
| **Accepted** | Event created successfully |
| **Rejected** | State / window / rule failed — see **Rejection Reason** |
| **Duplicate** | Same punch within tolerance window |

**Raw Punch Log is never discarded** for Rejected/Duplicate — only event creation is skipped.

### Common rejections

- Duplicate Check In  
- Check Out while still on Lunch/Tea break  
- Lunch/Tea Start without Check In  
- Second lunch or tea on the same day  
- Lunch/Tea punch outside time window  
- Any punch after Check Out (day COMPLETED)

---

## 6. Normal daily flow (6 punches)

Expected order:

```
Check In → WORKING
  → Lunch Start → (45 min) → Lunch End → WORKING
  → Tea Start → (15 min) → Tea End → WORKING
  → Check Out → COMPLETED
```

### Example day (PIN `1001`, 10-Aug-2026) — time-based routing

| Time | Event created (status code ignored) |
|------|--------------------------------------|
| 08:55 AM | Check In Check Out → Check In |
| 01:00 PM | Lunch Break → Break Start (lunch check in) |
| 01:45 PM | Lunch Break → Break End (lunch check out) |
| 04:00 PM | Tea Break → Break Start (tea check in) |
| 04:15 PM | Tea Break → Break End (tea check out) |
| 06:03 PM | Check In Check Out → Check Out |

Any single punch in the lunch window alternates Start → End. Same for tea.

**Biometric Attendance Day** for that employee/date will typically show:

- Late: **0** minutes (08:55 is before / within 9–10 AM window-in window)  
- Overtime: **3** minutes (after 18:00)  
- Lunch: expected 45, actual 45, excess 0, status Normal  
- Tea: expected 15, actual 15, excess 0, status Normal  
- Net working minutes = elapsed − break minutes  
- Current State: **COMPLETED**, Final Status: **Completed**

---

## 7. Biometric Attendance Day (what it stores)

One document per **Employee + Attendance Date**:

- Current State / Final Status  
- Regular Check In / Check Out  
- Late / Early Exit / Overtime flags and minutes  
- Lunch start/end, expected/actual/excess, status, Lunch Used  
- Tea start/end, expected/actual/excess, status, Tea Used  
- Total elapsed, total break, net working minutes  

Use this screen for daily HR review (not Punch Log, unless debugging).

---

## 8. Workspace: Biometric Integration

Desk workspace includes:

### Overview
- Number cards: **Punches Today**, **Pending Punches**, **Failed Syncs**
- Chart: **Punch Logs This Week**

### Quick Access (shortcuts with record counts)
Devices, Punch Logs, Pending Punches, Employee Checkin, Settings, Sync Logs, Employees  

Counts show **numbers only** (no “Active / Total / Pending” text).

### Masters & Operations (cards with record counts after the arrow)
- **Setup:** Biometric Settings, Biometric Device  
- **Operations:** Biometric Punch Log, Biometric Sync Log  
- **Attendance:** Biometric Check In Check Out, Lunch Break, Tea Break, Employee, Employee Checkin, Attendance  

---

## 9. Things you need

- Frappe bench running (`bench start`) — this site commonly uses port **8007**
- App `biometric_integration` installed (do **not** edit Frappe / ERPNext / HRMS core)
- ADMS-capable device (SenseFace / similar)
- Device and server on same LAN (or reachable public IP + port)
- Employees with **Attendance Device ID** = machine User ID / PIN
- HRMS installed if you want Employee Checkin / Auto Attendance
- Punch status codes configured on device **and** in Biometric Settings

---

## 10. Setup steps

### Step 1 — Open the workspace

Login → **Biometric Integration**.

### Step 2 — Biometric Settings

| Setting | Recommended |
|---------|-------------|
| Enabled | Yes |
| Accept Unknown Devices | Yes (first setup) |
| Create Attendance Events | Yes |
| Create Employee Checkin | Yes (if HRMS installed) |
| **Use Time-Based Punch Routing** | **Yes** (default) |
| Office Policy | 09:00–18:00; late after 10:00; lunch 12:00–15:00; tea 16:00–18:00; 45 / 15 min |
| Punch Status Mappings | Used only if time-based routing is Off |
| Enable TCP Pull | No (for SenseFace ADMS) |
| Enable Debug Logging | Yes only while troubleshooting |

### Step 3 — Biometric Device

| Field | Example |
|-------|---------|
| Device Name | SenseFace 2A |
| Serial Number | From Device Info (e.g. `NYU7254601554`) |
| IP Address | Device LAN IP (e.g. `192.168.10.201`) |
| Connection Mode | **ADMS Push** |
| TCP Port | 4370 (reference only; not used for ADMS) |

Do **not** use Pull Attendance when mode is ADMS Push.

### Step 4 — Machine Cloud Server (critical)

On device → **Cloud Server Setting**:

| Setting | Value |
|---------|--------|
| Server Mode | **ADMS** |
| Domain Name | OFF (when using IP) |
| Server Address | Frappe host IP (e.g. `192.168.10.30`) |
| Server Port | Frappe port (e.g. `8007`) |
| Proxy | OFF |

Device Ethernet example: IP `192.168.10.201`, Gateway `192.168.10.1`, DHCP OFF.

**WSL:** if Frappe runs in WSL, configure Windows portproxy so the device can reach `host:8007`.

### Step 5 — Test ADMS

Browser `/iclock` may show only `OK` — that is normal.

Real handshake:

```bash
curl "http://YOUR_IP:8007/iclock/cdata?SN=YOUR_SERIAL&options=all" -H "Host: site1.local"
```

Expect: `GET OPTION FROM: YOUR_SERIAL`.

### Step 6 — Link employees

| Machine PIN | Employee → Attendance Device ID |
|-------------|----------------------------------|
| 1001 | 1001 |
| 2 | 2 |

If wrong: Punch Log row appears, but no attendance events / Employee Checkin.

### Step 7 — Test full day (time-based)

Punch at these times (device status code does not matter):

1. Before 9:00 AM → Regular Check In  
2. Between 12:00–3:00 → Lunch Start  
3. Between 12:00–3:00 again → Lunch End  
4. Between 4:00–6:00 → Tea Start  
5. Between 4:00–6:00 again → Tea End  
6. After 6:00 PM → Regular Check Out  

Verify:

| Screen | Expect |
|--------|--------|
| Biometric Punch Log | 6 rows, Accepted |
| Biometric Check In Check Out | 2 rows |
| Biometric Lunch Break | 2 rows |
| Biometric Tea Break | 2 rows |
| Biometric Attendance Day | Summary COMPLETED |
| Biometric Device | Last Seen updated |
| Employee Checkin (if enabled) | 2 rows (IN + OUT only) |

---

## 11. HRMS Employee Checkin (optional)

Flow for **regular** Check In / Check Out only:

```
Biometric Check In Check Out → Employee Checkin → (Shift + Auto Attendance) → Attendance
```

Lunch and Tea stay in their own DocTypes — they are **not** sent as Employee Checkin.

### Off-Shift vs On-Shift

If Employee Checkin shows **Off-Shift**, HRMS did not find a shift for that punch time.

That is **not** controlled by Biometric Settings office hours.

You need in HRMS:

1. **Shift Type** (e.g. 09:00–18:00)  
2. **Shift Assignment** (or Employee Default Shift)  
3. Auto Attendance enabled on Shift Type if you want attendance marking  
4. Open checkin → **Fetch Shift** for old rows after assigning a shift  

Biometric Integration only creates the Employee Checkin row with Log Type IN/OUT and device id.

---

## 12. Admin regularization (forgotten punch)

Do **not** delete raw Punch Log rows for corrections.

1. Open **Biometric Attendance Regularization**  
2. New → Employee, Date, Event Category, Log Type, Corrected Time, Reason  
3. Submit  

Creates an event with **Is Regularized = Yes**, refreshes Attendance Day.  
Regularization can bypass lunch/tea **time window** checks when applying the corrected time.

API:

```
biometric_integration.api.regularize_attendance
```

Other APIs:

| Method | Purpose |
|--------|---------|
| `get_attendance_day_summary` | Refresh/return day summary |
| `pull_now` / `pull_device` | TCP pull (if enabled) |
| `test_device_connection` | TCP connectivity test |

---

## 13. Two ways to receive punches

### A) ADMS Push (recommended — current primary path)

Machine pushes to:

```
http://SERVER_IP:PORT/iclock/...
```

Handled by `page_renderer` → `ZKTecoADMSRenderer` → `adms.py` → `sync.py`.

### B) TCP Pull (optional, often fails on SenseFace)

ERPNext polls `IP:4370` via scheduler (`*/10 * * * *`) when **Enable TCP Pull** is on.  
SenseFace in ADMS mode usually refuses TCP pull (`BrokenPipe` / connection refused). Prefer ADMS.

---

## 14. Daily operations

- Machine sends punches automatically.  
- HR reviews **Biometric Attendance Day**.  
- Open **Biometric Punch Log** when status is Rejected / Duplicate.  
- Use Regularization for missing punches.  
- Keep Punch Log history for audit; delete only when intentionally clearing test data.

---

## 15. Common problems

### No punches in ERPNext
- Wrong Cloud Server IP/port on device  
- `bench start` not running  
- Firewall / WSL portproxy  
- Settings → Enabled = No  

### Punch Log exists, status Rejected
- Read **Rejection Reason**  
- Wrong sequence, outside lunch/tea window, or after Check Out  

### Punch Log exists, no events
- Create Attendance Events = Off  
- Employee Attendance Device ID not mapped  
- Punch Rejected/Duplicate  

### Browser shows only `OK` on `/iclock`
- Normal for ADMS API (not a login UI like eSSL portals)  
- Confirm via Punch Log / Device Last Seen  

### TCP Pull fails
- Use ADMS Push; set Connection Mode = ADMS Push  

### Late lunch/tea return
- Accepted if inside window; Attendance Day shows **Over Break** + excess minutes  

### Missing Check Out
- Attendance Day Final Status = **Incomplete**  
- Use Regularization  

### Employee Checkin Off-Shift
- Assign HRMS Shift Type / Shift Assignment (see section 11)  
- Biometric office policy alone does not fix Off-Shift  

---

## 16. Quick checklist

- [ ] App installed; `bench start` running  
- [ ] Biometric Settings enabled  
- [ ] Create Attendance Events = Yes  
- [ ] **Use Time-Based Punch Routing = Yes**  
- [ ] Office Policy: 09:00–18:00; **Late Entry After 10:00**; lunch window 12:00–15:00; tea window 16:00–18:00  
- [ ] Punch Status Mappings optional (only if time-based is Off)  
- [ ] Device serial/IP saved; Connection Mode = ADMS Push  
- [ ] Machine Cloud Server = ADMS, correct IP + port  
- [ ] Employee Attendance Device ID mapped  
- [ ] Test day: before 9 / lunch twice / tea twice / after 6 → Attendance Day COMPLETED  
- [ ] (Optional) HRMS Shift Type assigned before relying on On-Shift / Auto Attendance  

---

## 17. Code map (developers)

| Module | Role |
|--------|------|
| `adms.py` / `renderers.py` | ZKTeco `/iclock` ADMS endpoint |
| `sync.py` | Save Punch Log; call event processor; set Accepted/Rejected/Duplicate |
| `attendance_state.py` | Policy, day context, state machine, windows, duplicates, validation |
| `attendance_events.py` | Create events in the three DocTypes; optional Employee Checkin |
| `attendance_summary.py` | Calculate & upsert Biometric Attendance Day |
| `attendance_validation.py` | Desk/manual insert validation on event DocTypes |
| `regularization.py` | Admin corrections |
| `api.py` | Whitelisted desk APIs |
| `scheduler.py` / `zk_pull.py` | Optional TCP pull |
| `desk/workspace.py` | Workspace master-card record counts |
| `public/js/workspace_link_counts.js` | Show counts on Masters & Operations links |
| `install.py` | Role, default device seed, default punch mappings |

Hooks (`hooks.py`):

- `page_renderer` for `/iclock`  
- cron TCP pull every 10 minutes  
- `app_include_js` for workspace counts  
- override `frappe.desk.desktop.get_desktop_page` for card counts  

Run tests:

```bash
bench --site site1.local set-config allow_tests true
bench --site site1.local run-tests --app biometric_integration
```

---

## 18. Need help? Where to look

| Screen | Check |
|--------|-------|
| Biometric Punch Log | Did punch arrive? Accepted / Rejected / Duplicate? |
| Biometric Attendance Day | State, late, overtime, break excess, net hours |
| Biometric Device → Last Seen | Is machine talking to server? |
| Biometric Sync Log | TCP pull errors |
| Error Log | Enable Debug Logging in Settings for ADMS traces |
| Employee Checkin | Only Regular In/Out; Off-Shift → fix HRMS shift |
