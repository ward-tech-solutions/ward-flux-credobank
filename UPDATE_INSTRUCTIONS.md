# 🚀 Update Instructions for CredoBank Server

## ✅ Changes Pushed to GitHub

The following improvements have been added:

### 1️⃣ SNMP/ICMP Monitoring Badges
- Device cards now show monitoring type badges:
  - 📶 **ICMP** badge (blue) - Always visible for all devices
  - 📡 **SNMP** badge (green) - Shows when SNMP community is configured
- Table view has new "Monitoring" column with badges
- Easy visual identification of monitoring capabilities

### 2️⃣ Improved Add Device Form
- **Organized sections**:
  - Basic Information (Hostname, IP Address)
  - Location (Region, Branch)
  - Monitoring Configuration (SNMP settings)
- **Info box** explaining monitoring types
- **Better styling** with clear visual hierarchy
- **Disabled SNMP version** when no community string entered
- **Helper text** explaining when SNMP is enabled

### 3️⃣ Diagnostic Script
- Added `DIAGNOSE_SERVER.sh` to troubleshoot deployment issues
- Checks:
  - ✅ Container status
  - ✅ Database tables existence
  - ✅ Seeding status
  - ✅ Device counts (should be 875)
  - ✅ SNMP vs ICMP device breakdown
  - ✅ Monitoring task activity
  - ✅ Health check recording

---

## 📦 Deploy Updates to CredoBank Server

### Step 1: Pull Latest Changes

SSH into your CredoBank server and run:

```bash
cd ward-flux-credobank
git pull origin main
```

### Step 2: Rebuild and Restart Containers

```bash
# Rebuild with new frontend changes
docker-compose -f docker-compose.production-local.yml build

# Restart all services
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml up -d
```

### Step 3: Run Diagnostic Script

```bash
# Make script executable
chmod +x DIAGNOSE_SERVER.sh

# Run diagnostics
./DIAGNOSE_SERVER.sh
```

This will show you:
- ✅ If all containers are running
- ✅ If database tables exist
- ✅ How many devices are being monitored
- ✅ SNMP vs ICMP device breakdown
- ✅ If monitoring tasks are working

### Step 4: Clear Browser Cache

**IMPORTANT:** The frontend has changed, so you need to clear your browser cache:

1. Open your browser
2. Press `Ctrl+Shift+Delete` (Windows/Linux) or `Cmd+Shift+Delete` (Mac)
3. Select "Cached images and files"
4. Click "Clear data"
5. Refresh the page (`Ctrl+F5` or `Cmd+Shift+R`)

Or just open in incognito/private mode to see the changes immediately.

---

## 🎨 What You'll See After Update

### Monitor Page - Grid View
Each device card will now show:
```
┌─────────────────────────────────┐
│ 🔴 Ninotsminda-PayBox           │
│ Samtskhe-Javakheti              │
│ 10.159.69.12                    │
│ 📶 ICMP  📡 SNMP  ← NEW!        │
│ ⚠️  Down 5m • RECENT             │
└─────────────────────────────────┘
```

### Monitor Page - Table View
New "Monitoring" column:
```
| Status | Device Name      | ... | Monitoring          | Response |
|--------|------------------|-----|---------------------|----------|
| 🟢     | Telavi-PayBox    | ... | 📶 ICMP  📡 SNMP    | 3.2ms    |
| 🟢     | Khulo-ATM        | ... | 📶 ICMP             | 5.1ms    |
```

### Add Device Form
Now organized with clear sections:

```
┌─────────────────────────────────────────┐
│  Add New Device                         │
├─────────────────────────────────────────┤
│                                         │
│  Basic Information                      │
│  ───────────────────                    │
│  Hostname:    [               ]         │
│  IP Address:  [192.168.1.1   ]         │
│                                         │
│  Location                               │
│  ────────                               │
│  Region:      [Select Region ▼]        │
│  Branch:      [               ]         │
│                                         │
│  Monitoring Configuration               │
│  ────────────────────────               │
│  ┌─────────────────────────────────┐   │
│  │ ℹ️  Monitoring Types:            │   │
│  │ • ICMP (Ping) - Always enabled  │   │
│  │ • SNMP - Optional, enter below  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  SNMP Community (Optional):             │
│  [public             ]                  │
│  Leave empty for ICMP-only monitoring   │
│                                         │
│  SNMP Version: [SNMPv2c     ▼]          │
│                                         │
├─────────────────────────────────────────┤
│     [Cancel]          [Add Device]      │
└─────────────────────────────────────────┘
```

---

## ❓ How to Know What's Working

### ICMP-Only Device
- Shows only 📶 **ICMP** badge (blue)
- Gets ping monitoring every 60 seconds
- No SNMP data collection

### ICMP + SNMP Device
- Shows 📶 **ICMP** + 📡 **SNMP** badges
- Gets ping monitoring every 60 seconds
- Gets SNMP data collection for detailed metrics

### To Add ICMP-Only Device:
1. Click "Add Device"
2. Enter Hostname and IP
3. Select Region and Branch
4. **Leave SNMP Community EMPTY**
5. Click "Add Device"

### To Add ICMP + SNMP Device:
1. Click "Add Device"
2. Enter Hostname and IP
3. Select Region and Branch
4. **Enter SNMP Community** (e.g., "public")
5. Select SNMP Version (v1, v2c, or v3)
6. Click "Add Device"

---

## 🐛 Troubleshooting

### Issue: Not seeing the badges?
**Fix:** Clear browser cache and hard refresh (`Ctrl+F5`)

### Issue: Database errors in diagnostic script
**Fix:** Database wasn't seeded properly. Run:
```bash
docker exec wardops-api-prod python3 /app/scripts/seed_core.py
docker exec wardops-api-prod python3 /app/scripts/seed_credobank.py
docker-compose -f docker-compose.production-local.yml restart
```

### Issue: Add Device form looks the same
**Fix:** Frontend didn't rebuild. Run:
```bash
docker-compose -f docker-compose.production-local.yml build api
docker-compose -f docker-compose.production-local.yml restart api
```

### Issue: SNMP badge not showing for devices with SNMP community
**Fix:** Check if `snmp_community` field is set in database:
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT hostname, snmp_community FROM devices WHERE snmp_community IS NOT NULL LIMIT 10;"
```

---

## 📊 Verify Everything is Working

After deployment, run the diagnostic script:

```bash
cd ward-flux-credobank
./DIAGNOSE_SERVER.sh
```

You should see:
- ✅ All 5 containers running and healthy
- ✅ 875 devices in database
- ✅ Device count breakdown (SNMP vs ICMP-only)
- ✅ Health checks being recorded
- ✅ Ping monitoring tasks succeeding

---

## 🎉 You're Done!

Your CredoBank deployment now has:
- ✅ Visual SNMP/ICMP badges on all devices
- ✅ Improved Add Device form with clear sections
- ✅ Monitoring type explanation for users
- ✅ Diagnostic script for troubleshooting
- ✅ Better UX for understanding device monitoring capabilities

**GitHub Repository:** https://github.com/ward-tech-solutions/ward-flux-credobank

**Latest Commit:** `1a75b63` - Add SNMP/ICMP monitoring badges and improve Add Device form
