# down_since Timestamp Backfill

## Problem Description

**User Report:** "Device shows 'Down 10m' but it's been DOWN for 7 days according to VictoriaMetrics charts"

**Symptoms:**
- Devices that have been DOWN for days show "Down 10m" (or similar short duration)
- VictoriaMetrics historical data shows device has been DOWN for much longer
- `down_since` timestamp in database is recent (from worker restart) instead of historical

**Example:**
```
Device: Tbilisi SW Test (192.168.200.77)
Database down_since: 2025-10-24 13:23:41 (11 minutes ago)
VictoriaMetrics data: Shows DOWN since 7 days ago
UI displays: "Down 11m" ❌ Should show: "Down 7d" ✓
```

---

## Root Cause

When the monitoring worker restarts:

1. Worker queries device from database: `device = db.query(StandaloneDevice).filter_by(id=device_uuid).first()`
2. Device has existing `down_since` timestamp from BEFORE the restart
3. First ping after restart fails (device is DOWN)
4. Logic calculates: `previous_state = device.down_since is None = False` (down_since exists)
5. Current ping: `current_state = False` (still DOWN)
6. State transition check: `not current_state and previous_state` = `True and False` = **FALSE**
7. Falls through to: `elif not current_state and device.down_since is None` = **FALSE**
8. **Result:** down_since should be preserved... ✓

**BUT THE ISSUE IS:**

Before Phase 4, the `down_since` timestamps were being managed by the old `ping_device()` task in `tasks.py`, which had different logic. When we deployed Phase 4:

1. Old task stopped running (replaced by batch tasks)
2. Some devices had stale or NULL `down_since` values
3. Worker restart triggered the "Device is DOWN but down_since was NULL" logic (line 215-218)
4. Set `down_since = utcnow()` instead of querying VictoriaMetrics for historical downtime start

**The actual root cause:** `down_since` field in PostgreSQL doesn't match the REAL downtime start stored in VictoriaMetrics historical data.

---

## Solution: Backfill from VictoriaMetrics

We need to query VictoriaMetrics historical data to find when each DOWN device ACTUALLY went down, and update the database accordingly.

### Backfill Script

**File:** `scripts/backfill_down_since_from_vm.py`

**What it does:**
1. Queries all devices with `down_since` set (currently DOWN)
2. For each device:
   - Queries VictoriaMetrics for last 30 days of `device_ping_status` data
   - Walks backwards through time to find when device went DOWN (1 → 0 transition)
   - Compares with current `down_since` in database
   - If difference > 1 hour, updates database with correct historical timestamp

**Example output:**
```
Checking Tbilisi SW Test (192.168.200.77)...
  📝 Backfilling Tbilisi SW Test:
     Current: 2025-10-24 13:23:41 (down for 0:11:00)
     Actual:  2025-10-17 08:15:32 (down for 7 days, 5:08:09)

✅ Backfill complete:
   - Backfilled: 15 devices
   - Skipped: 5 devices (already correct)
   - Total: 20 devices
```

---

## Deployment

### On Credobank Server

```bash
cd /home/wardops/ward-flux-credobank

# Pull the backfill script
git pull origin main

# Run the backfill
docker exec wardops-api-prod python3 scripts/backfill_down_since_from_vm.py
```

**Note:** This can also be run from the monitoring worker container:
```bash
docker exec wardops-worker-monitoring-prod python3 scripts/backfill_down_since_from_vm.py
```

---

## Verification

### 1. Check Before Backfill

```bash
# Check Tbilisi SW Test current down_since
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT name, ip, down_since, NOW() - down_since as current_downtime FROM standalone_devices WHERE ip = '192.168.200.77';"
```

**Expected:**
```
name       | ip             | down_since          | current_downtime
-----------+----------------+---------------------+-----------------
Tbilisi SW | 192.168.200.77 | 2025-10-24 13:23:41 | 00:11:00
```

### 2. Run Backfill

```bash
docker exec wardops-api-prod python3 scripts/backfill_down_since_from_vm.py
```

### 3. Check After Backfill

```bash
# Check updated down_since
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT name, ip, down_since, NOW() - down_since as actual_downtime FROM standalone_devices WHERE ip = '192.168.200.77';"
```

**Expected:**
```
name       | ip             | down_since          | actual_downtime
-----------+----------------+---------------------+----------------
Tbilisi SW | 192.168.200.77 | 2025-10-17 08:15:32 | 7 days 05:08:09
```

### 4. Check UI

Refresh the Monitor page and click on "Tbilisi SW Test" device.

**Expected:**
- Status badge shows "Down 7d" (or similar long duration)
- Availability timeline shows full downtime history
- Matches VictoriaMetrics chart data

---

## Why This Happened

### Timeline of Events

1. **Phase 1-3 (VictoriaMetrics Migration):**
   - Dual-write to PostgreSQL + VictoriaMetrics
   - `down_since` managed by old `ping_device()` task
   - Everything working correctly

2. **Phase 4 Deployment (Oct 24, ~13:20):**
   - Stopped PostgreSQL writes to `ping_results`
   - Switched to batch processing (`ping_devices_batch`)
   - Worker restarted

3. **First Ping After Restart:**
   - Device "Tbilisi SW Test" was already DOWN for 7 days
   - But `down_since` in database might have been NULL or stale
   - Logic: "Device is DOWN but down_since is NULL" → set `down_since = NOW()`
   - **Result:** Lost 7 days of downtime history

4. **State Transition Fix:**
   - Fixed the logic to use `device.down_since` for previous state
   - But this doesn't recover the lost historical timestamps
   - Need backfill to restore correct downtime start times

### Prevention

**Going forward, this won't happen again because:**

1. ✅ State transition logic is now correct (uses `device.down_since` not `ping_results`)
2. ✅ Worker restarts preserve existing `down_since` timestamps
3. ✅ New DOWN events correctly set `down_since = NOW()`
4. ✅ Recovery events correctly clear `down_since = NULL`
5. ✅ "RECOVERED" messages appear in logs when devices come back UP

**The backfill is a ONE-TIME operation** to fix the historical data discrepancy caused by the Phase 4 deployment worker restart.

---

## Technical Details

### VictoriaMetrics Query

The backfill script queries VictoriaMetrics using `query_range`:

```python
query = f'device_ping_status{{device_id="{device_id}"}}'
params = {
    "query": query,
    "start": int(start_time.timestamp()),  # 30 days ago
    "end": int(end_time.timestamp()),      # now
    "step": "5m"                            # 5-minute resolution
}
```

**Response format:**
```json
{
  "status": "success",
  "data": {
    "result": [{
      "values": [
        [1729756800, "1"],  // Oct 24 08:00 - UP
        [1729757100, "0"],  // Oct 24 08:05 - DOWN ← found it!
        [1729757400, "0"],  // Oct 24 08:10 - DOWN
        ...
      ]
    }]
  }
}
```

### Algorithm

1. Get all timestamps with status values
2. Walk **backwards** from most recent
3. Track when we first see status=0 (DOWN)
4. Keep going back until we find status=1 (UP) → this is the transition point
5. Return the timestamp where status changed from 1 → 0

**Edge cases:**
- If device never shows UP in last 30 days → use oldest DOWN timestamp
- If no data in VictoriaMetrics → skip (can't backfill)
- If current `down_since` matches VictoriaMetrics (< 1 hour diff) → skip

---

## Impact

### Before Backfill
- ❌ Downtime durations show from worker restart time (10-30 minutes)
- ❌ Historical downtime data lost
- ❌ Can't trust downtime metrics
- ❌ False "device just went down" alerts

### After Backfill
- ✅ Downtime durations show true historical length (days/weeks)
- ✅ Matches VictoriaMetrics chart data
- ✅ Accurate downtime tracking
- ✅ Reliable metrics for SLA reporting

---

## Related Files

- `scripts/backfill_down_since_from_vm.py` - Backfill script
- `monitoring/tasks_batch.py` - State transition logic (fixed)
- `DEVICE-STATUS-BUG-FIX.md` - Original state transition fix
- `utils/victoriametrics_client.py` - VictoriaMetrics query client

---

## Frequency

**Run this script:**
- ✅ **Once** after Phase 4 deployment (to fix historical data)
- ❌ **Not needed** for routine operations (state transitions now work correctly)
- ⚠️  **Only if** you restart workers and notice downtime durations reset

Future worker restarts won't need backfill because the state transition logic now correctly preserves `down_since` timestamps.
