# HOTFIX: Device Status Display Bug

## Critical Issue

**Device showing UP (green) in monitor grid when actually DOWN!**

### Symptoms:
- Zabbix sends alert: "ICMP Ping: Unavailable" ✅ CORRECT
- Device detail view shows "Down - Not responding" ✅ CORRECT
- Availability chart shows device is down ✅ CORRECT
- **Monitor grid shows GREEN "UP" indicator** ❌ WRONG!

### Example Device:
- Name: `RuckusAP-AP (10.195.5.17)`
- Database: `down_since = 2025-10-24 14:42:42` (device IS down)
- UI: Shows green "UP" status (WRONG!)

---

## Root Cause

The API was using **VictoriaMetrics ping data** to determine device status instead of the authoritative `device.down_since` field in PostgreSQL.

**Problem:** VictoriaMetrics data can be stale/cached, while `down_since` is updated immediately by the monitoring worker.

**File:** `routers/devices_standalone.py` lines 131-151

**Bad Logic (Before):**
```python
if ping_result:
    is_reachable = ping_result.get("is_reachable", False)
    ping_status = "Up" if is_reachable else "Down"  # ❌ Using VM data!
```

**Good Logic (After):**
```python
# Use device.down_since as SOURCE OF TRUTH
if obj.down_since is not None:
    ping_status = "Down"  # ✅ Device IS down
else:
    ping_status = "Up"   # ✅ Device IS up
```

---

## The Fix

**Changed:** `routers/devices_standalone.py`

**Commit:** `e123567` - "CRITICAL FIX: Device status showing wrong (green when DOWN)"

**What Changed:**
1. **Device status now determined by `down_since` field** (source of truth)
2. VictoriaMetrics data only used for response time and timestamp
3. No more status discrepancies between database and UI

---

## Deployment on Credobank Server

### Step 1: Pull Latest Code

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
```

**Expected output:**
```
Updating d43cc3a..e123567
Fast-forward
 routers/devices_standalone.py | 20 ++++++++++----------
 1 file changed, 13 insertions(+), 7 deletions(-)
```

### Step 2: Rebuild API Container

```bash
docker-compose -f docker-compose.production-priority-queues.yml build api
```

**Expected:** Build completes in ~30-60 seconds

### Step 3: Restart API Container

```bash
# Stop current API
docker-compose -f docker-compose.production-priority-queues.yml stop api

# Remove old container
docker ps -a | grep api
docker rm wardops-api-prod

# Start new container
docker-compose -f docker-compose.production-priority-queues.yml up -d api
```

### Step 4: Verify API is Healthy

```bash
docker ps | grep api
# Should show "healthy" status

curl http://localhost:5001/health
# Should return {"status": "healthy"}
```

### Step 5: Clear Redis Cache (Optional but Recommended)

The device list is cached in Redis for 30 seconds. Clear cache to see fix immediately:

```bash
docker exec wardops-redis-prod redis-cli FLUSHDB
```

---

## Testing the Fix

### Test Case 1: Verify RuckusAP Device Shows as DOWN

1. Open browser: `http://flux.credobank.ge:5001/monitor`
2. Search for `10.195.5.17` or `RuckusAP`
3. **Expected:** Device card shows **RED** with "Down" status
4. Click on the device
5. **Expected:** Detail view also shows "Down - Not responding"

### Test Case 2: Force a Device Down and Check Status

```bash
# Pick a test device IP (not production!)
TEST_IP="10.x.x.x"

# Simulate device going down (set down_since timestamp)
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "UPDATE standalone_devices SET down_since = NOW() WHERE ip = '$TEST_IP';"

# Wait 5 seconds for cache to expire
sleep 5

# Check UI - device should show RED "Down" status
```

### Test Case 3: Device Recovery

```bash
# Clear down_since (simulate recovery)
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "UPDATE standalone_devices SET down_since = NULL WHERE ip = '$TEST_IP';"

# Wait 5 seconds
sleep 5

# Check UI - device should show GREEN "Up" status
```

---

## Technical Details

### Source of Truth

**Device Status:** `standalone_devices.down_since` field (PostgreSQL)
- `down_since IS NULL` → Device is UP
- `down_since HAS TIMESTAMP` → Device is DOWN

**Updated By:** `monitoring/tasks_batch.py` lines 177-220
- Sets `down_since = utcnow()` when device goes down
- Sets `down_since = NULL` when device recovers

### Data Flow

```
1. Monitoring Worker pings device (every 30s)
2. Worker updates standalone_devices.down_since in PostgreSQL
3. API reads device from PostgreSQL
4. API uses down_since to determine ping_status
5. Frontend displays status (Green=Up, Red=Down)
```

### Why NOT VictoriaMetrics?

VictoriaMetrics is great for **metrics and charts**, but not for **real-time status**:
- ❌ Data propagation delay (seconds)
- ❌ Can be cached
- ❌ Not transactional with database updates

PostgreSQL `down_since` is perfect for **real-time status**:
- ✅ Updated immediately by monitoring worker
- ✅ Transactional (consistent)
- ✅ No propagation delay

---

## Verification Queries

### Check Devices Currently Marked as DOWN

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT name, ip, down_since FROM standalone_devices WHERE down_since IS NOT NULL ORDER BY down_since DESC LIMIT 10;"
```

### Check Monitoring Worker Logs

```bash
docker logs wardops-worker-monitoring-prod --tail 100 | grep -E "went DOWN|RECOVERED"
```

**Expected output:**
```
✅ Device Zugdidi2-881 (10.195.74.248) RECOVERED
❌ Device RuckusAP-AP (10.195.5.17) went DOWN
```

---

## Impact

**Before Fix:**
- Operators see green "UP" status
- Zabbix alerts "device down"
- Confusion: "Why is Zabbix alerting if device is up?"
- Manual refresh doesn't help (cached in API)

**After Fix:**
- UI shows RED "Down" status immediately
- Matches Zabbix alerts
- Operators can trust the UI
- No more status discrepancies

---

## Rollback Plan

If this fix causes issues:

```bash
cd /home/wardops/ward-flux-credobank
git revert e123567
git push origin main

# Rebuild and restart API
docker-compose -f docker-compose.production-priority-queues.yml build api
docker-compose -f docker-compose.production-priority-queues.yml up -d api
```

---

## Related Issues Fixed

This fix also resolves:
- Issue #1: "Devices showing up but Zabbix alerting"
- Issue #2: "Status in grid doesn't match detail view"
- Issue #3: "Refresh doesn't update device status"

All caused by the same root issue: API using VM data instead of down_since field.

---

## Notes

- **No database migration required** (uses existing down_since column)
- **No monitoring worker changes** (already updates down_since correctly)
- **Only API endpoint changed** (device list response)
- **Redis cache auto-expires** (30-second TTL, but can flush for immediate effect)
- **Frontend unchanged** (already handles ping_status correctly)

---

## Support

After deployment, monitor for 1 hour:

```bash
# Watch API logs for errors
docker logs -f wardops-api-prod

# Check device status consistency
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT
    COUNT(*) FILTER (WHERE down_since IS NULL) as up_count,
    COUNT(*) FILTER (WHERE down_since IS NOT NULL) as down_count
  FROM standalone_devices WHERE enabled = true;"
```

If you see any status inconsistencies, check the logs and report back.
