# How to Implement Biometric Integration

Simple step-by-step guide in plain English.

---

## What this app does

1. Employee puts face / finger on the biometric machine.
2. Machine sends the punch to your ERPNext / Frappe server.
3. App saves the punch.
4. App creates **Employee Checkin** (if HRMS is installed).
5. ERPNext can then make **Attendance** from those checkins.

```
Machine  →  Frappe App  →  Punch Log  →  Employee Checkin  →  Attendance
```

---

## Things you need

- Frappe / ERPNext running
- This app: `biometric_integration` (already installed on your site)
- Your biometric machine (example: PT/BF/OFC/PM/01)
- Machine and server on the same network (or machine can reach the server on the internet)
- Employee list in ERPNext
- HRMS app (recommended) for Employee Checkin and Attendance

---

## Step 1: Open the app in ERPNext

1. Login to ERPNext Desk.
2. Search for **Biometric Integration**.
3. Open that workspace.

You will see:
- **Biometric Settings**
- **Biometric Device**
- **Biometric Punch Log**
- **Biometric Sync Log**

---

## Step 2: Turn on settings

1. Open **Biometric Settings**.
2. Keep **Enabled** = Yes (checked).
3. Keep **Create Employee Checkin** = Yes.
4. Keep **Accept Unknown Devices** = Yes (good for first setup).
5. Save.

Optional later:
- Turn on **Enable TCP Pull** only if push from machine does not work.

---

## Step 3: Check your device record

1. Open **Biometric Device**.
2. Open device **PT/BF/OFC/PM/01**.

Make sure these look correct:

| Field | Example value |
|-------|----------------|
| Device Name | PT/BF/OFC/PM/01 |
| IP Address | 192.168.1.183 |
| TCP Port | 4370 |
| Serial Number | Replace `PENDING-SN` with real Serial Number from machine |

How to find Serial Number on machine:
- Go to machine menu → Device Info / System Info
- Copy Serial Number (SN)
- Paste it in ERPNext and Save

If you leave `PENDING-SN`, the app can update it when the machine first connects.

---

## Step 4: Set the machine Cloud Server (most important)

On the biometric machine screen:

1. Open **Cloud Server Setting**
2. Set:

| Setting | What to put |
|---------|-------------|
| Server Mode | **ADMS** |
| Enable Domain Name | OFF if using IP, ON if using website name |
| Server Address | Your Frappe server IP or website name (do **not** leave `0.0.0.0`) |
| Server Port | **80** for HTTP, or **443** for HTTPS |
| Enable Proxy Server | OFF |

3. Save settings on the machine.
4. Restart the machine if it asks.

### Simple meaning

- The machine must know **where your ERPNext server is**.
- Right now your machine shows Server Address = `0.0.0.0` → that means “no server”. Change it.
- Do **not** put port `4370` here. Port `4370` is only for local pull.
- For Cloud / ADMS, use your website port (`80` or `443`).

Example:
- If your ERPNext opens as `http://192.168.1.50`, then:
  - Server Address = `192.168.1.50`
  - Server Port = `80`

---

## Step 5: Link employees

On the machine, each person has a User ID / PIN (like 1, 2, 3).

In ERPNext:

1. Open **Employee**.
2. Open one employee.
3. Find field **Attendance Device ID**.
4. Put the same number as on the machine (example: `1`).
5. Save.

Do this for every employee.

| Machine User ID | Employee Attendance Device ID |
|-----------------|-------------------------------|
| 1 | 1 |
| 2 | 2 |
| 3 | 3 |

If this is wrong, punches will save in Punch Log but will **not** become Employee Checkin.

---

## Step 6: Test

### Test A — Push (best method)

1. Make one punch on the machine (face or finger).
2. Wait 1–2 minutes.
3. In ERPNext open **Biometric Punch Log**.
4. You should see a new row.
5. Open **Biometric Device** → check **Last Seen** time updated.

If Last Seen updates, machine is talking to Frappe. Good.

### Test B — Pull (backup method)

Use this only if push does not work.

1. In Biometric Settings, enable **TCP Pull**, Save.
2. Open your Biometric Device.
3. Click **Test TCP Connection**.
4. If success, click **Pull Attendance**.
5. Check **Biometric Punch Log**.

Machine must be reachable at `192.168.1.183` port `4370`.

---

## Step 7: Attendance in ERPNext

1. Install **HRMS** if not installed.
2. Make sure employees have **Shift Assignment**.
3. Enable **Auto Attendance** on Shift Type.
4. Employee Checkin will create Attendance automatically.

Flow:

```
Punch on machine
   → Biometric Punch Log
   → Employee Checkin
   → Attendance
```

---

## Daily use (after setup)

You normally do nothing.

- Machine sends punches by itself (ADMS push).
- You only check Punch Log / Sync Log if something looks wrong.

---

## Common problems (simple fixes)

### 1) No punches in ERPNext
- Check machine Server Address is not `0.0.0.0`
- Check server IP is correct
- Check machine and server are on same network / internet
- Check Biometric Settings is Enabled

### 2) Punch Log comes, but no Employee Checkin
- Employee **Attendance Device ID** is missing or wrong
- HRMS / Employee Checkin is not installed
- Create Employee Checkin is turned OFF in Settings

### 3) TCP Test fails
- Wrong IP (should be `192.168.1.183` for this machine)
- Port must be `4370`
- Machine is offline / different network
- Firewall blocking port 4370

### 4) Serial Number still PENDING-SN
- Enter real SN from machine Device Info
- Or wait for first successful ADMS connection

---

## Quick checklist

- [ ] App installed
- [ ] Biometric Settings enabled
- [ ] Device IP / port filled
- [ ] Real Serial Number saved
- [ ] Machine Cloud Server = ADMS
- [ ] Machine Server Address = Frappe IP / domain
- [ ] Machine Server Port = 80 or 443
- [ ] Employee Attendance Device ID mapped
- [ ] Test punch appears in Punch Log
- [ ] HRMS ready for Employee Checkin / Attendance

---

## Two ways to get data (remember this)

1. **ADMS Push (recommended)**  
   Machine sends data to ERPNext automatically.

2. **TCP Pull (optional)**  
   ERPNext goes to machine IP `192.168.1.183:4370` and downloads data.

Use Push first. Use Pull only if Push cannot work.

---

## Need help?

Check these screens in Desk:
- **Biometric Punch Log** → Did punch arrive?
- **Biometric Sync Log** → Any error?
- **Biometric Device → Last Seen** → Is machine online with server?

That is enough to know where the problem is.
