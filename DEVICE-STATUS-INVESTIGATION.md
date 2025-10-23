# Device Status Mismatch Investigation

**Issue:** User reported that "khargauli was down but UI said it is UP"
**Date:** 2025-10-23
**Priority:** High

---

## Problem Description

User observed that device "Kharagauli" was actually DOWN (not responding), but the Monitor page UI was showing it as UP.

---

## How Device Status Works

### Backend (Python/FastAPI)

1. **Ping Task** ([monitoring/tasks.py:178-329](monitoring/tasks.py#L178-L329))
   - Runs every 30 seconds for all enabled devices
   - Performs ICMP ping (2 packets, 1 second timeout)
   - Saves `PingResult` to database with `is_reachable` field
   - Updates `StandaloneDevice.down_since` timestamp:
     - **Device is UP** (`is_alive = True`): Clears `down_since = None`
     - **Device is DOWN** (`is_alive = False`): Sets `down_since = current_timestamp`

2. **Device List API** ([routers/devices_standalone.py:204-250](routers/devices_standalone.py#L204-L250))
   - Gets latest ping result using `DISTINCT ON` (optimized query)
   - Sets `ping_status`:
     ```python
     if ping_result:
         ping_status = "Up" if ping_result.is_reachable else "Down"
     ```
   - Returns both `ping_status` and `down_since` to frontend

### Frontend (React/TypeScript)

1. **Status Display** ([frontend/src/pages/Monitor.tsx:76-102](frontend/src/pages/Monitor.tsx#L76-L102))
   - Shows downtime duration if **BOTH**:
     - `device.ping_status === 'Down'`
     - `device.down_since` is set
   - Shows "Down" if `ping_status === 'Down'` but no `down_since`
   - Shows nothing (UP) if `ping_status === 'Up'`

2. **Auto-refresh**
   - React Query refetches every 30 seconds
   - WebSocket updates (real-time)

---

## Possible Root Causes

### 1. **Database Transaction Not Committed (FIXED)**
- **Status:** ✅ FIXED in hotfix (commit fb30bdd)
- **Issue:** DB session was held open during SNMP polling
- **Fix:** Close DB session immediately after queries, before network operations
- **Impact:** This could have caused `down_since` updates to not be committed

### 2. **Race Condition Between Ping and API Query**
- **Status:** ⚠️ Possible
- **Issue:** API query might read device BEFORE ping task commits `down_since` update
- **Scenario:**
  1. Device goes DOWN at 10:00:00
  2. Ping task detects DOWN, sets `down_since`, but commit delayed
  3. API query at 10:00:01 reads device (still sees `down_since = None`)
  4. User sees device as UP despite being DOWN
- **Likelihood:** Low (commit should be fast)
- **Fix:** Ensure `db.commit()` happens immediately after `down_since` update

### 3. **Frontend Caching**
- **Status:** ⚠️ Possible
- **Issue:** React Query might show stale data
- **Mitigation:** React Query is configured with 30s refetch interval
- **Check:** Browser DevTools → Network → Check if API is being called

### 4. **Ping Timeout Too Short**
- **Status:** ⚠️ Possible
- **Current:** 1 second timeout, 2 packets
- **Issue:** Some devices (especially across slow networks) might take > 1s to respond
- **Result:** Device marked as DOWN even though it's actually UP (just slow)
- **Check:** Review ping logs for devices with intermittent UP/DOWN states

### 5. **Ping Task Not Running**
- **Status:** ⚠️ Possible
- **Issue:** Celery workers might be down or overloaded
- **Check:**
  ```bash
  docker exec wardops-worker-prod celery -A celery_app inspect active
  docker logs wardops-worker-prod | grep "Pinging.*devices"
  ```

### 6. **Latest Ping Query Returns Wrong Result**
- **Status:** ⚠️ Possible
- **Issue:** `DISTINCT ON` query might return stale ping result
- **Current Query:**
  ```python
  db.query(PingResult)
    .filter(PingResult.device_ip.in_(ips))
    .distinct(PingResult.device_ip)
    .order_by(PingResult.device_ip, PingResult.timestamp.desc())
    .all()
  ```
- **Check:** Verify query returns truly latest ping

---

## Diagnostic Steps

### Step 1: Run Diagnostic Script

```bash
cd /home/wardops/ward-ops-credobank
python3 diagnose_device_status.py khargauli
```

**What it checks:**
- Device exists and is enabled
- Current `down_since` value
- Latest 10 ping results with timestamps
- Detects inconsistencies between `ping_result.is_reachable` and `device.down_since`
- Checks ping timing intervals

### Step 2: Check Ping Task Logs

```bash
docker logs wardops-worker-prod --tail 100 | grep -E "(khargauli|Khargauli)"
```

**Look for:**
- ✅ Device went DOWN logs
- ✅ Device RECOVERED logs
- ⚠️ Errors during ping
- ⚠️ Missing expected logs

### Step 3: Check Database Directly

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    name,
    ip,
    enabled,
    down_since,
    updated_at
FROM standalone_devices
WHERE LOWER(name) LIKE '%khargauli%';
"
```

### Step 4: Check Latest Ping Results

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    device_ip,
    device_name,
    is_reachable,
    avg_rtt_ms,
    packet_loss_percent,
    timestamp
FROM ping_results
WHERE device_ip IN (
    SELECT ip FROM standalone_devices WHERE LOWER(name) LIKE '%khargauli%'
)
ORDER BY timestamp DESC
LIMIT 10;
"
```

### Step 5: Monitor Real-Time Updates

```bash
# Terminal 1: Watch ping task
docker logs wardops-worker-prod -f | grep -E "(Pinging|khargauli|DOWN|RECOVERED)"

# Terminal 2: Watch API requests
docker logs wardops-api-prod -f | grep -E "devices/standalone/list"

# Terminal 3: Check database updates
watch -n 2 "docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \"
SELECT name, ip, down_since, updated_at
FROM standalone_devices
WHERE LOWER(name) LIKE '%khargauli%';
\""
```

---

## Potential Fixes

### Fix 1: Ensure Immediate Commit After down_since Update

**File:** [monitoring/tasks.py:286](monitoring/tasks.py#L286)

**Current:**
```python
        db.commit()
        logger.debug(f"Ping complete for {device_ip}: is_alive={host.is_alive}, down_since={device.down_since if device else 'N/A'}")
```

**Already correct** - commit happens immediately after down_since update.

### Fix 2: Add Transaction Isolation

If race conditions are the issue, we could add explicit transaction isolation:

```python
# Before updating down_since
db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
```

### Fix 3: Increase Ping Timeout for Remote Devices

If false negatives are the issue:

```python
# Current: timeout=1 second
host = ping(device_ip, count=2, interval=0.2, timeout=1, privileged=False)

# Proposed: timeout=2 seconds for slow networks
host = ping(device_ip, count=3, interval=0.2, timeout=2, privileged=False)
```

### Fix 4: Add Retry Logic for Ping Failures

Only mark device as DOWN after 2 consecutive ping failures:

```python
# Check if device was DOWN in previous ping too
previous_2_pings = db.query(PingResult).filter(
    PingResult.device_ip == device_ip
).order_by(PingResult.timestamp.desc()).limit(2).all()

# Only set down_since if device failed 2 consecutive pings
if len(previous_2_pings) >= 1 and not previous_2_pings[0].is_reachable:
    # Confirmed DOWN (2 consecutive failures)
    if not device.down_since:
        device.down_since = utcnow()
```

### Fix 5: Add Logging for Debugging

Add more detailed logging to track state transitions:

```python
logger.info(f"[PING] {device.name} ({device_ip}): "
            f"current={current_state}, previous={previous_state}, "
            f"down_since={device.down_since}, "
            f"rtt={host.avg_rtt}ms, loss={host.packet_loss}%")
```

---

## Next Steps

1. ✅ **Deploy hotfix** (already done - commit fb30bdd)
   - Fixed idle transaction leak
   - Fixed NameError in device ping

2. 🔍 **Run diagnostic script** on production
   ```bash
   python3 diagnose_device_status.py khargauli
   ```

3. 📊 **Monitor for 24 hours**
   - Watch ping task logs
   - Check for any DOWN→UP or UP→DOWN transitions
   - Verify `down_since` is being updated correctly

4. 🐛 **If issue persists:**
   - Collect diagnostic output
   - Check if specific to Kharagauli device or affects others
   - Consider implementing Fix 4 (retry logic) or Fix 3 (longer timeout)

---

## Expected Behavior After Hotfix

After the hotfix is deployed:

1. ✅ **Device goes DOWN:**
   - Ping task detects `is_alive = False`
   - Sets `device.down_since = current_timestamp`
   - Commits transaction immediately
   - API returns `ping_status = "Down"` and `down_since`
   - UI shows device as DOWN with downtime duration

2. ✅ **Device comes UP:**
   - Ping task detects `is_alive = True`
   - Clears `device.down_since = None`
   - Resolves any active alerts
   - Commits transaction immediately
   - API returns `ping_status = "Up"` and `down_since = null`
   - UI shows device as UP (no downtime)

3. ✅ **No more idle transactions:**
   - DB sessions closed before network operations
   - Idle transaction count < 5 (was 45-51)
   - Transactions commit within milliseconds

---

## Contact

If issue persists after diagnostic steps, provide:

1. Output of diagnostic script
2. Logs from ping task for affected device
3. Screenshots of UI showing issue
4. Exact timestamp when issue was observed

---

**Last Updated:** 2025-10-23
**Status:** Investigation in progress, hotfix deployed
