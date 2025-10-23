# Ping Diagnostic Investigation - Device Not Being Monitored

**Date:** 2025-10-23
**Status:** 🔍 INVESTIGATING
**Priority:** 🚨 CRITICAL - Real-time monitoring missing downtimes

---

## 🚨 Problem

**Symptom:** Device goes DOWN but WARD OPS doesn't detect it

**Specific Evidence:**
- **Device:** PING-Kutaisi4-AP (10.195.83.252)
- **External Alert:** Zabbix showed device DOWN from 17:14:33 to 17:19:33 (~5 minutes)
- **WARD OPS:** Shows device UP with 100% uptime, no alerts
- **Database:** Last ping recorded at 13:01:21 (27+ minutes before investigation)
- **Current Time:** 13:28:28 (when investigation started)

**User Quote:** _"restart is not SOLUTION!"_

---

## ✅ What We Know (Facts)

### Database Status
```sql
-- Device EXISTS and is ENABLED
SELECT id, name, ip, enabled FROM standalone_devices WHERE ip = '10.195.83.252';
Result:
  id: 06add57f-bed8-4a2b-982f-31c5eaa3189c
  name: PING-Kutaisi4-AP
  ip: 10.195.83.252
  enabled: true ✅
```

### Scheduler Status
```bash
# Beat IS running and scheduling ping-all-devices every 30 seconds
docker logs wardops-beat-prod --tail 50 | grep "ping-all-devices"
Result: Continuous scheduling at :18 and :48 of each minute ✅
```

### Worker Status
```bash
# Worker IS processing ping tasks successfully
docker logs wardops-worker-prod --tail 500 | grep "Pinged"
Result: Many successful pings for OTHER devices ✅

# Worker NOT pinging target device
docker logs wardops-worker-prod --tail 500 | grep "10.195.83.252"
Result: NO output (no pings for this IP) ❌
```

### Ping History
```sql
-- Last ping was 27+ minutes ago
SELECT device_name, device_ip, is_reachable, timestamp, NOW() - timestamp AS age
FROM ping_results
WHERE device_ip = '10.195.83.252'
ORDER BY timestamp DESC LIMIT 10;

Result: Latest ping at 2025-10-23 13:01:21 (age: 00:27:06+) ❌
```

---

## 🔍 Investigation Hypothesis

**The `ping_all_devices` task is NOT retrieving this specific device from the database query.**

**Possible Root Causes:**

### 1. Database Query Filter Issue (Most Likely)
**Hypothesis:** The query `db.query(StandaloneDevice).filter_by(enabled=True).all()` is not returning device 10.195.83.252

**Why this might happen:**
- Database session isolation level issue
- Stale connection with outdated snapshot
- SQLAlchemy caching old query results
- Database transaction not committed when device was enabled
- Race condition between device update and query execution

**Evidence needed:**
- Log total devices retrieved
- Log all device IPs in the query result
- Check if target device is in the list

### 2. Monitoring Profile Issue (Less Likely)
**Hypothesis:** Monitoring profile check is failing silently

**Code:**
```python
profile = db.query(MonitoringProfile).filter_by(is_active=True).first()
if not profile:
    return  # Silent exit!
```

**Why this might happen:**
- No active monitoring profile in database
- Profile was disabled

**Evidence needed:**
- Log when no profile found
- Check if function returns early

### 3. Device IP Field Empty/Null (Unlikely)
**Hypothesis:** Device record exists but `ip` field is None or empty string

**Code:**
```python
for device in devices:
    if device.ip:  # Skip if ip is None or empty
        ping_device.delay(str(device.id), device.ip)
```

**Why unlikely:**
- Database shows ip = '10.195.83.252'
- Ping results table has historical data with this IP

**Evidence needed:**
- Log devices with null/empty IP

### 4. Task Queue Backlog (Unlikely)
**Hypothesis:** Ping tasks are queued but not executing due to worker overload

**Why unlikely:**
- Worker is processing OTHER device pings successfully
- Only THIS specific device is missing

---

## 🛠️ Diagnostic Changes Made

### Added Comprehensive Logging to `ping_all_devices()`

**Location:** `monitoring/tasks.py` lines 340-388

**Logging Added:**
1. **Total devices retrieved:** `"Retrieved {len(devices)} enabled devices from database"`
2. **All device IPs:** `"Device IPs to ping: [list of IPs]"`
3. **Target device check:** Specifically looks for 10.195.83.252 in results
4. **Device found:** `"Found target device 10.195.83.252 - ID: ..., Name: ..., Enabled: ..."`
5. **Device missing:** `"Target device 10.195.83.252 NOT FOUND in enabled devices query!"`
6. **Database investigation:** If missing, checks:
   - Total device count in database
   - Whether device exists but with `enabled=false`
   - Whether device exists at all
7. **Scheduled count:** `"Scheduled {scheduled_count} ping tasks"`

### Added Logging to `ping_device()`

**Location:** `monitoring/tasks.py` line 203-204

**Logging Added:**
- `"EXECUTING ping for TARGET device 10.195.83.252 (ID: ...)"`

This confirms if the ping task is actually being CALLED for the target device.

---

## 🚀 Deployment

### Run Diagnostic Deployment

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
./deploy-diagnostic-logging.sh
```

**What it does:**
1. Rebuilds worker and beat containers with new logging
2. Restarts containers
3. Waits 35 seconds for one ping cycle
4. Shows diagnostic output from logs

---

## 📊 Expected Diagnostic Results

### Scenario 1: Device NOT Retrieved from Database (Most Likely)

**Expected logs:**
```
ping_all_devices: Retrieved 874 enabled devices from database
ping_all_devices: Device IPs to ping: [10.x.x.x, 10.y.y.y, ...] (no 10.195.83.252)
ping_all_devices: Target device 10.195.83.252 NOT FOUND in enabled devices query!
ping_all_devices: Total devices in database: 875
ping_all_devices: Device 10.195.83.252 exists but enabled=true
```

**Root Cause:** SQLAlchemy query not returning the device despite `enabled=true`

**Solutions:**
- Force database session refresh before query
- Use explicit `db.expire_all()` before query
- Check isolation level and transaction state
- Add explicit `db.commit()` before query to ensure fresh snapshot

### Scenario 2: Device Retrieved but Not Scheduled

**Expected logs:**
```
ping_all_devices: Retrieved 875 enabled devices from database
ping_all_devices: Device IPs to ping: [..., 10.195.83.252, ...]
ping_all_devices: Found target device 10.195.83.252 - ID: 06add57f..., Name: PING-Kutaisi4-AP, Enabled: True
ping_all_devices: Scheduled 875 ping tasks
(No "EXECUTING ping for TARGET device" message)
```

**Root Cause:** Device scheduled but ping task not executing

**Solutions:**
- Check Celery task routing
- Check Redis task queue
- Verify worker is consuming from correct queue

### Scenario 3: Device Retrieved and Scheduled but Ping Fails

**Expected logs:**
```
ping_all_devices: Found target device 10.195.83.252
ping_all_devices: Successfully scheduled ping for target device 10.195.83.252
ping_device: EXECUTING ping for TARGET device 10.195.83.252 (ID: 06add57f...)
Error pinging 10.195.83.252: [error message]
```

**Root Cause:** Ping execution failing silently

**Solutions:**
- Check ICMP permissions
- Check network connectivity from worker container
- Verify timeout not too short

### Scenario 4: No Active Monitoring Profile

**Expected logs:**
```
ping_all_devices: No active monitoring profile found
```

**Root Cause:** Monitoring disabled at profile level

**Solutions:**
- Check monitoring_profiles table
- Enable monitoring profile

---

## 🔧 Monitoring Instructions

### 1. Watch Logs in Real-Time

```bash
# Watch for diagnostic messages
docker logs wardops-worker-prod -f | grep -E '(ping_all_devices|10.195.83.252)'
```

**Run this for 2-3 minutes** to capture at least 4-5 ping cycles (every 30 seconds).

### 2. Check Recent Diagnostic Output

```bash
# Last 100 lines with diagnostic context
docker logs wardops-worker-prod --tail 100 | grep -A 5 -B 5 "ping_all_devices"
```

### 3. Verify Beat Scheduling

```bash
# Confirm ping-all-devices is being scheduled
docker logs wardops-beat-prod --tail 50 | grep "ping-all-devices"
```

**Expected:** Entries every 30 seconds at :18 and :48 of each minute.

### 4. Check Database Directly

```bash
# Verify device still exists and enabled
docker exec wardops-postgres-prod psql -U postgres -d wardops -c \
  "SELECT id, name, ip, enabled, created_at FROM standalone_devices WHERE ip = '10.195.83.252';"
```

### 5. Check Monitoring Profile

```bash
# Verify monitoring is enabled
docker exec wardops-postgres-prod psql -U postgres -d wardops -c \
  "SELECT id, name, is_active FROM monitoring_profiles;"
```

---

## 🎯 Next Steps Based on Results

### If device NOT in query results:
1. **Immediate fix:** Force session refresh
2. **Code change:** Add `db.expire_all()` before query in ping_all_devices
3. **Root cause:** Investigate SQLAlchemy session caching behavior
4. **Testing:** Verify device appears after fix

### If device in query but not scheduled:
1. **Check:** Celery task routing configuration
2. **Check:** Redis queue status (`celery -A celery_app inspect active`)
3. **Check:** Worker consuming correct queues
4. **Testing:** Manual task submission

### If task submitted but not executing:
1. **Check:** Worker logs for task receipt
2. **Check:** Network connectivity from worker container
3. **Check:** ICMP ping permissions
4. **Testing:** Manual ping from worker container: `docker exec wardops-worker-prod ping -c 2 10.195.83.252`

### If no monitoring profile:
1. **Check:** Database monitoring_profiles table
2. **Create:** Active monitoring profile if missing
3. **Verify:** Profile activation in UI

---

## 📋 Known Facts Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| **Device in DB** | ✅ EXISTS | Query returns record with enabled=true |
| **Device enabled** | ✅ TRUE | enabled column is true |
| **Beat scheduling** | ✅ WORKING | Schedules ping-all-devices every 30s |
| **Worker running** | ✅ WORKING | Processing pings for other devices |
| **Worker pinging target** | ❌ NO | No logs for 10.195.83.252 |
| **Recent pings** | ❌ STALE | Last ping 27+ minutes ago |
| **Datetime bugs** | ✅ FIXED | No errors in logs |
| **Memory issues** | ✅ FIXED | 32% RAM usage |

---

## 🎯 Success Criteria

After deploying diagnostics, we should be able to determine:

1. **Is the device retrieved from database?** (YES/NO)
2. **Is the device scheduled for ping?** (YES/NO)
3. **Is the ping task executing?** (YES/NO)
4. **Where exactly is the failure point?** (Query / Schedule / Execute)

This will allow us to implement a **targeted fix** instead of "restart and hope."

---

**Created:** 2025-10-23 18:45
**Status:** Diagnostic logging deployed, awaiting results
**Priority:** 🚨 CRITICAL - Root cause analysis in progress
**User Requirement:** "restart is not SOLUTION!" - Need permanent fix

---

## 📞 User Action Required

**Deploy the diagnostic logging:**
```bash
ssh wardops@credobank-server
cd /home/wardops/ward-flux-credobank
git pull origin main
./deploy-diagnostic-logging.sh
```

**Then monitor logs for 2-3 minutes:**
```bash
docker logs wardops-worker-prod -f | grep -E '(ping_all_devices|10.195.83.252)'
```

**Report back with:**
1. Total devices retrieved
2. Whether 10.195.83.252 is in the device list
3. Whether ping task is executing for this IP
4. Any error messages

This will tell us exactly WHERE the problem is occurring.
