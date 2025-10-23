# Real-Time Status Issue - Devices Show UP When DOWN

**Date:** 2025-10-23 15:47
**Status:** 🔍 INVESTIGATING
**Priority:** CRITICAL - Real-Time Monitoring Issue

---

## 🚨 Issue Report

**Problem:** Devices show as UP in WARD OPS, but they're actually DOWN (ping timeouts)

**User Report:**
- Time: 15:41-15:47 (6 minute window)
- Devices affected:
  - Kharagauli-ATM (10.199.78.163) - DOWN since 15:41
  - Kharagauli-PayBox (10.159.78.11) - DOWN since 15:44
  - Kharagauli-PayBox (10.159.78.15) - DOWN since 15:44
  - Kharagauli-AP (10.195.78.252) - DOWN since 15:44
  - Kharagauli-NVR (10.199.78.140) - DOWN since 15:44

**Evidence:**
- User confirmed: "EVEN PINGS are timing out"
- Zabbix alerts showing: "ICMP Ping: Unavailable by ICMP ping"
- But WARD OPS UI shows: Green status (UP) with response times

**Delay:** 3-6 minutes between actual downtime and UI update

---

## 🔍 Analysis

### Expected Behavior (Normal)

1. **Ping Schedule:** Every 30 seconds
2. **Detection Time:** Within 30 seconds max
3. **UI Update:** Within 60 seconds (30s ping + 30s cache)
4. **Alert Creation:** Immediate (same ping cycle)

### Actual Behavior (Broken)

1. **Device goes DOWN:** 15:41
2. **UI still shows UP:** 15:47 (6 minutes later!)
3. **Alerts not visible:** Not showing in WARD OPS
4. **Cache may be stale:** Showing old ping results

---

## 🔎 Possible Root Causes

### Cause 1: Celery Worker Not Running or Overloaded

**Symptoms:**
- Ping tasks not executing
- Task queue building up
- No recent ping results in database

**Check:**
```bash
docker ps | grep celery
docker logs wardops-celery-worker --tail 50 | grep ping
```

**Fix:**
```bash
docker-compose -f docker-compose.production-local.yml restart celery-worker celery-beat
```

### Cause 2: Ping Results Stale in Database

**Symptoms:**
- Latest ping timestamp > 1 minute old
- `is_reachable` doesn't match actual status
- `down_since` not being set

**Check:**
```sql
SELECT device_name, device_ip, is_reachable, timestamp,
       NOW() - timestamp AS age
FROM ping_results
WHERE device_name ILIKE '%Kharagauli%'
ORDER BY timestamp DESC LIMIT 5;
```

**Fix:**
- Check Celery worker logs for errors
- Ensure ping task is running every 30 seconds

### Cause 3: Frontend Cache Showing Stale Data

**Symptoms:**
- API returns correct status (DOWN)
- But UI shows old status (UP)
- Cache TTL expired but not refreshing

**Check:**
```bash
# Check Redis cache
docker exec wardops-redis-prod redis-cli KEYS "devices:list:*"
docker exec wardops-redis-prod redis-cli TTL "devices:list:..."

# Test API directly
curl http://localhost:5001/api/v1/devices/standalone/list
```

**Fix:**
```bash
# Clear Redis cache
docker exec wardops-redis-prod redis-cli FLUSHDB

# Or wait 30 seconds for cache to expire
```

### Cause 4: Database Query Not Using Latest Ping

**Symptoms:**
- Ping results ARE fresh in database
- But device list API returns old status
- Query logic issue

**Check:**
- Look at `_latest_ping_lookup()` function
- Ensure it's using MAX timestamp correctly

**Fix:**
- Already fixed in query optimization (subquery approach)

### Cause 5: down_since Not Being Set

**Symptoms:**
- Device is DOWN (`is_reachable = false`)
- But `down_since` is NULL
- UI interprets NULL as UP

**Check:**
```sql
SELECT name, ip, down_since
FROM standalone_devices
WHERE ip IN ('10.199.78.163', '10.159.78.11', '10.159.78.15');
```

**Fix:**
- Check ping task code (lines 257-284)
- Ensure down_since is set when device goes DOWN

### Cause 6: Alert Creation Not Working

**Symptoms:**
- Devices go DOWN
- But no alerts created in alert_history
- Alert page shows nothing

**Check:**
```sql
SELECT * FROM alert_history
WHERE triggered_at > NOW() - INTERVAL '10 minutes'
ORDER BY triggered_at DESC;
```

**Fix:**
- Check ping task code (lines 264-279)
- Ensure alert creation logic is working

---

## 🛠️ Diagnostic Steps

### Step 1: Run Diagnostic Script

```bash
cd /path/to/ward-ops-credobank
./diagnose-realtime-status.sh
```

This script checks:
1. Celery worker status
2. Ping task schedule
3. Latest ping results
4. Device down_since timestamps
5. Redis cache status
6. Recent alerts
7. Actual ping tests

### Step 2: Check Celery Workers

```bash
# Are workers running?
docker ps | grep celery

# Check worker logs
docker logs wardops-celery-worker --tail 100

# Check beat logs (scheduler)
docker logs wardops-celery-beat --tail 100

# Inspect active tasks
docker exec wardops-celery-worker celery -A celery_app inspect active
```

### Step 3: Check Latest Ping Results

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT device_name, device_ip, is_reachable, timestamp, NOW() - timestamp AS age
FROM ping_results
WHERE device_name ILIKE '%Kharagauli%'
ORDER BY timestamp DESC
LIMIT 10;
"
```

**Expected:** Age < 1 minute
**If age > 1 minute:** Ping tasks not running!

### Step 4: Check Device Status

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, ip, down_since, enabled
FROM standalone_devices
WHERE name ILIKE '%Kharagauli%';
"
```

**Expected:** DOWN devices have `down_since` set
**If NULL:** Status update logic broken!

### Step 5: Clear Redis Cache (Quick Fix)

```bash
# Clear all cached device lists
docker exec wardops-redis-prod redis-cli FLUSHDB

# Wait 1-2 seconds for fresh data
# Then refresh browser
```

---

## 🔧 Quick Fixes

### Fix 1: Restart Celery Workers

If workers are stuck or not processing tasks:

```bash
docker-compose -f docker-compose.production-local.yml restart celery-worker celery-beat
```

**Wait:** 1 minute
**Then:** Check if status updates

### Fix 2: Clear Redis Cache

If cache is stale:

```bash
docker exec wardops-redis-prod redis-cli FLUSHDB
```

**Wait:** 30 seconds for fresh ping
**Then:** Refresh browser

### Fix 3: Force Immediate Ping

Manually trigger ping for specific devices:

```bash
docker exec wardops-api-prod python3 -c "
from monitoring.tasks import ping_device
ping_device('DEVICE_UUID', '10.199.78.163')
"
```

### Fix 4: Check Monitoring Profile

Ensure monitoring is enabled:

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT * FROM monitoring_profiles WHERE is_active = true;
"
```

If no active profile, monitoring is disabled!

---

## 📊 Current System Configuration

**Ping Schedule:**
- Task: `monitoring.tasks.ping_all_devices`
- Frequency: Every 30 seconds
- Timeout: 1 second per ping
- Count: 2 pings per device

**Expected Timeline:**
- T+0s: Device goes DOWN
- T+30s: Next ping cycle detects DOWN
- T+30s: `down_since` set, alert created
- T+30s: Database updated
- T+60s: Cache expires (30s TTL)
- T+60s: Frontend fetches fresh data
- **Total delay: Max 60 seconds**

**Actual Timeline (Broken):**
- T+0s: Device goes DOWN
- T+360s: Still shows UP (6 minutes!)
- **Something is wrong!**

---

## 🎯 Long-Term Solutions

### Solution 1: Reduce Ping Interval (Quick Win)

**Change:** 30 seconds → 15 seconds

```python
# monitoring/celery_app.py
"ping-all-devices": {
    "task": "monitoring.tasks.ping_all_devices",
    "schedule": 15.0,  # Every 15 seconds (was 30)
},
```

**Impact:** Faster detection (15s instead of 30s)

### Solution 2: Reduce Cache TTL

**Change:** 30 seconds → 10 seconds

```python
# routers/devices_standalone.py
redis_client.setex(cache_key, 10, ...)  # 10s instead of 30s
```

**Impact:** Fresher data in UI (max 10s stale)

### Solution 3: Implement WebSocket Updates (Tier 2)

**Change:** Push updates instead of polling

**Benefits:**
- Instant UI updates (< 1 second)
- No cache delay
- Real-time experience

**Effort:** Medium (Tier 2 optimization)

### Solution 4: Add Health Monitoring

**Add:** Monitor Celery worker health

```python
@shared_task
def check_celery_health():
    # Check if workers are processing tasks
    # Alert if queue is backing up
    # Alert if no pings in last 2 minutes
```

---

## ✅ Verification After Fix

1. **Wait 1 minute** after applying fix
2. **Take down a test device** (disconnect network)
3. **Watch the dashboard:**
   - Should turn RED within 30-60 seconds
   - Should show "Down Xm Ys"
   - Alert should appear in alerts page
4. **Bring device back up**
5. **Watch the dashboard:**
   - Should turn GREEN within 30-60 seconds
   - "Down since" should clear
   - Alert should be resolved

---

## 📝 Investigation Checklist

Run through this checklist on CredoBank server:

- [ ] Run `./diagnose-realtime-status.sh`
- [ ] Check Celery worker status (Section 1)
- [ ] Check ping task logs (Section 2)
- [ ] Check latest ping results age (Section 3)
- [ ] Check down_since timestamps (Section 4)
- [ ] Check Redis cache TTL (Section 5)
- [ ] Check recent alerts (Section 6)
- [ ] Test actual pings (Section 7)
- [ ] Identify root cause from above
- [ ] Apply appropriate fix
- [ ] Verify fix works

---

## 🚨 Critical Questions

1. **Are Celery workers running?**
   - Check: `docker ps | grep celery`
   - If NO: Start them immediately!

2. **Are ping tasks executing?**
   - Check: `docker logs wardops-celery-worker | grep ping`
   - If NO: Check worker logs for errors

3. **Are ping results fresh?**
   - Check: Database query (age < 1 minute)
   - If NO: Celery worker issue

4. **Is cache stale?**
   - Check: Redis TTL
   - If stale: Clear cache

5. **Is monitoring enabled?**
   - Check: monitoring_profiles table
   - If NO: Enable it!

---

**Next Action:** Run diagnostic script on CredoBank server to identify root cause

**Script:** `./diagnose-realtime-status.sh`

**Then:** Apply appropriate fix based on findings

---

**Created:** 2025-10-23 15:50
**Status:** Awaiting diagnostic results
**Priority:** CRITICAL - Affects real-time monitoring reliability
