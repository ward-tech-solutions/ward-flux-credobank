# Downtime Calculation Fix - Deployment Guide

**Date:** October 21, 2025
**Issue:** Devices showing "Down 4h" when they actually went down 3 minutes ago
**Fix:** Proper state transition detection + timezone-aware timestamps

---

## What Was Fixed

### Root Cause
1. **Stale timestamps** - `down_since` was only set when `None`, so old values persisted
2. **No state transition detection** - System didn't compare current vs previous ping state
3. **No timezone awareness** - Using `datetime.utcnow()` without timezone info

### Solution Implemented

**File:** `monitoring/tasks.py`

1. **Proper State Transition Detection:**
   ```python
   # Query previous ping to compare states
   previous_ping = db.query(PingResult).filter(...).first()
   current_state = host.is_alive
   previous_state = previous_ping.is_reachable if previous_ping else True

   # UP -> DOWN: Set down_since
   if previous_state and not current_state:
       device.down_since = utcnow()

   # DOWN -> UP: Clear down_since
   elif not previous_state and current_state:
       device.down_since = None
   ```

2. **Timezone-Aware Timestamps:**
   ```python
   def utcnow():
       return datetime.now(timezone.utc)  # Timezone-aware
   ```

3. **Self-Healing Edge Cases:**
   - Device UP but has `down_since`: Clear it (stale data)
   - Device DOWN but no `down_since`: Set it now (missing data)

---

## Deployment Steps

### Step 1: Pull Latest Code

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
```

**Expected output:**
```
From https://github.com/ward-tech-solutions/ward-flux-credobank
   3224225..9abd995  main       -> origin/main
Updating 3224225..9abd995
Fast-forward
 monitoring/tasks.py | 50 ++++++++++++++++++++++++++++++++++++++++++--------
 1 file changed, 39 insertions(+), 11 deletions(-)
```

### Step 2: Restart Worker Container

The worker container runs the ping tasks, so it needs to be restarted:

```bash
docker-compose -f docker-compose.production-local.yml restart wardops-worker-prod
```

**Expected output:**
```
Restarting wardops-worker-prod ... done
```

### Step 3: Verify Worker Started

```bash
docker logs wardops-worker-prod --tail 50
```

**Look for:**
```
[2025-10-21 XX:XX:XX,XXX: INFO/MainProcess] celery@XXXXXX ready.
[tasks]
  . monitoring.tasks.ping_device
  ...
```

---

## Verification & Testing

### Test 1: Check Current Down Devices

**Before fix:** Devices show "Down 4h" with stale timestamps

**After fix:** Devices will show correct downtime

1. Open Monitor page
2. Look at currently down devices
3. Check browser console (F12) for debug logs:
   ```
   [Device-Name] down_since: 2025-10-21T09:42:33Z
   Date: 2025-10-21T09:42:33.000Z
   Diff hours: 0.05
   ```

### Test 2: Simulate Device Going Down

1. **Unplug a test device or block its IP**

2. **Wait 30 seconds for ping task to run**

3. **Check worker logs:**
   ```bash
   docker logs wardops-worker-prod --tail 20 -f
   ```

   **Expected log:**
   ```
   INFO Device TestDevice (10.1.2.3) went DOWN (UP->DOWN transition)
   ```

4. **Check Monitor page:**
   - Device should appear at top of list
   - Downtime should show "< 1m" or "Xm" (correct minutes)

### Test 3: Device Coming Back Up

1. **Plug device back in or unblock IP**

2. **Wait 30 seconds**

3. **Check worker logs:**
   ```bash
   docker logs wardops-worker-prod --tail 20 -f
   ```

   **Expected log:**
   ```
   INFO Device TestDevice (10.1.2.3) came back UP after 0:02:30 (DOWN->UP transition)
   ```

4. **Check Monitor page:**
   - Device should disappear from "Recently Down" section
   - Or move to "Available" section

### Test 4: Stale Data Self-Healing

The fix includes self-healing logic. Check logs for these warnings:

```bash
docker logs wardops-worker-prod | grep "stale\|missing"
```

**Expected warnings (if stale data exists):**
```
WARNING Device XYZ (10.1.2.3) is UP but has stale down_since timestamp - clearing it
WARNING Device ABC (10.1.2.4) is DOWN but missing down_since timestamp - setting it now
```

These warnings are GOOD - they show the system is fixing inconsistent data automatically.

---

## Expected Behavior After Fix

### Scenario 1: Device Goes Down
- **Trigger:** Ping fails (UP → DOWN)
- **Action:** `down_since` set to current UTC time
- **Log:** `Device X went DOWN (UP->DOWN transition)`
- **UI:** Shows "< 1m" immediately

### Scenario 2: Device Comes Back Up
- **Trigger:** Ping succeeds (DOWN → UP)
- **Action:** `down_since` cleared (set to NULL)
- **Log:** `Device X came back UP after HH:MM:SS (DOWN->UP transition)`
- **UI:** Device moves to Available section

### Scenario 3: Stale Timestamp (Device UP, but has down_since)
- **Trigger:** Ping succeeds, but `down_since` exists
- **Action:** `down_since` cleared automatically
- **Log:** `WARNING ... is UP but has stale down_since timestamp - clearing it`
- **UI:** Device shows as Available (correct)

### Scenario 4: Missing Timestamp (Device DOWN, but no down_since)
- **Trigger:** Ping fails, but `down_since` is NULL
- **Action:** `down_since` set to current time
- **Log:** `WARNING ... is DOWN but missing down_since timestamp - setting it now`
- **UI:** Device shows downtime from now forward

---

## Troubleshooting

### Problem: Still seeing "Down 4h" after deployment

**Check 1: Did worker restart?**
```bash
docker ps | grep worker
docker logs wardops-worker-prod --tail 5
```

**Check 2: Are pings running?**
```bash
docker logs wardops-worker-prod | grep "ping_device" | tail -10
```

**Check 3: Database has stale data**

If devices still have stale timestamps, wait for next ping cycle (30 seconds). The self-healing logic will fix it automatically.

**Or force immediate fix:**
```bash
# Restart worker to trigger fresh pings
docker-compose -f docker-compose.production-local.yml restart wardops-worker-prod
```

### Problem: Logs show "is UP but has stale down_since timestamp"

**This is GOOD!** It means the self-healing logic is working. The warning shows the system detected and fixed stale data.

After a few ping cycles, these warnings should stop appearing (data is clean).

### Problem: Frontend still shows wrong time

**Clear browser cache:**
- Chrome/Firefox: `Ctrl+Shift+R` or `Cmd+Shift+R`
- Or use incognito window

**Check browser console:**
Open DevTools (F12) and look for the debug logs showing actual timestamps.

---

## Monitoring Post-Deployment

### Day 1: Watch for State Transitions

```bash
# Follow worker logs
docker logs wardops-worker-prod -f | grep -E "went DOWN|came back UP|stale|missing"
```

### Day 2-3: Verify Accuracy

1. Compare downtime shown in UI with actual device outage time
2. Check Zabbix alerts vs tool downtime display
3. Verify devices at top of Monitor page are actually most recently down

### Week 1: Check for Edge Cases

```bash
# Check for any unexpected warnings
docker logs wardops-worker-prod | grep -i "ERROR\|WARNING" | grep down_since
```

---

## Rollback Plan (If Needed)

If the fix causes issues:

```bash
cd /home/wardops/ward-flux-credobank

# Checkout previous version
git checkout 3224225

# Restart worker
docker-compose -f docker-compose.production-local.yml restart wardops-worker-prod
```

**Then report the issue with:**
- Worker logs (`docker logs wardops-worker-prod`)
- Specific device that showed wrong downtime
- Expected vs actual downtime values

---

## Summary of Changes

**Files Modified:**
- `monitoring/tasks.py` (ping_device function)

**Lines Changed:** ~50 lines (39 added, 11 modified)

**Backward Compatible:** Yes - uses existing database schema

**Database Migration Required:** No

**Downtime Required:** No (just worker restart)

**Risk Level:** Low (only affects downtime display, not monitoring itself)

---

## Success Criteria

✅ Devices showing correct downtime (matches actual outage time)
✅ Recently down devices appear at top of Monitor page
✅ Stale timestamps automatically cleaned up
✅ State transition logs visible in worker logs
✅ No errors in worker logs related to down_since

---

## Next Steps After Deployment

1. **Monitor for 24 hours** - Watch logs for any unexpected behavior
2. **Validate accuracy** - Compare tool downtime with actual outage times
3. **Remove debug logging** - Once confirmed working, remove console.log from Monitor.tsx
4. **Document baseline** - Record typical ping intervals and transition detection speed

---

**Deployment Time:** ~2 minutes (git pull + worker restart)
**Testing Time:** ~5 minutes (simulate down/up transitions)
**Monitoring Period:** 24-48 hours

Ready to deploy!
