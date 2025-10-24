# Downtime Calculation Debug Guide

## Issue Summary

**Problem:** Device downtime showing incorrect duration (e.g., "Down 11m" when should show "Down 17m")

**Observed Behavior:**
- Database shows: `down_since = 2025-10-24 16:03:52.052638` (UTC)
- Current UTC time: `2025-10-24 16:20:13`
- Expected downtime: ~17 minutes
- **Actual display: "Down 11m"** ❌

**Device:** RuckusAP-AP (10.195.5.17)

---

## Root Cause Analysis

### What We Know:

✅ **Database is correct:**
```sql
down_since = 2025-10-24 16:03:52.052638 (UTC)
```

✅ **PostgreSQL timezone is correct:**
```
timezone = UTC
```

✅ **Server timezone is correct:**
```
Tbilisi: Fri Oct 24 08:20:13 PM +04 2025
UTC:     Fri Oct 24 04:20:13 PM UTC 2025
(+4 hour offset)
```

✅ **Monitoring worker not resetting timestamp:**
```
Checked logs - no state transitions for this device
```

### What We Need to Verify:

❓ **API Response Format:**
- Does `down_since` have 'Z' suffix?
- Expected: `"2025-10-24T16:03:52.052638Z"`
- Without Z: `"2025-10-24T16:03:52.052638"` (would cause timezone issues)

❓ **Frontend Calculation:**
- Is JavaScript parsing UTC correctly?
- Is browser timezone causing offset?
- Is there caching of old data?

---

## Debugging Steps

### Step 1: Check if Timezone Fix is Deployed

Run this on the Credobank server:

```bash
cd /home/wardops/ward-flux-credobank
bash check-timezone-fix.sh
```

**Expected Output:**
```
✅ TIMEZONE FIX DEPLOYED - timestamp has Z suffix
down_since: 2025-10-24T16:03:52.052638Z
```

**If Not Deployed:**
```
❌ TIMEZONE FIX NOT DEPLOYED - timestamp missing Z suffix
down_since: 2025-10-24T16:03:52.052638
```

Then deploy the fix:
```bash
bash deploy-ui-fixes.sh
```

---

### Step 2: Check Frontend Calculation (Browser Console)

1. Open the UI: http://10.30.25.46:5001/monitor
2. Press F12 to open DevTools
3. Click on "Console" tab
4. Look for debug output like this:

```
[PING-RuckusAP-AP_10.195.5.17] down_since: 2025-10-24T16:03:52.052638Z
Date: 2025-10-24T16:03:52.052Z
Diff hours: 0.27
```

**Analyze the output:**

- `down_since`: Should have 'Z' at the end ✅
- `Date`: Should match the down_since time ✅
- `Diff hours`: Should match actual elapsed time ✅

**Manual Verification in Console:**

Run these commands in the browser console:

```javascript
// 1. Check browser current time
console.log('Browser time:', new Date().toString())
console.log('Browser UTC:', new Date().toISOString())

// 2. Parse the down_since timestamp
const downSince = new Date("2025-10-24T16:03:52.052638Z")
console.log('Parsed down_since:', downSince.toString())
console.log('Parsed UTC:', downSince.toISOString())

// 3. Calculate difference
const now = Date.now()
const downSinceMs = downSince.getTime()
const diffMs = now - downSinceMs
const diffMin = Math.floor(diffMs / (1000 * 60))
console.log('Difference (milliseconds):', diffMs)
console.log('Difference (minutes):', diffMin)

// 4. Check for timezone offset issues
const offset = new Date().getTimezoneOffset()
console.log('Browser timezone offset (minutes):', offset)
console.log('Expected offset for Tbilisi (GMT+4):', -240)
```

**Expected Output (if working correctly):**

```
Browser time: Fri Oct 24 2025 20:20:00 GMT+0400 (Georgia Standard Time)
Browser UTC: 2025-10-24T16:20:00.000Z
Parsed down_since: Fri Oct 24 2025 20:03:52 GMT+0400 (Georgia Standard Time)
Parsed UTC: 2025-10-24T16:03:52.052Z
Difference (milliseconds): 1008000
Difference (minutes): 16
Browser timezone offset (minutes): -240
Expected offset for Tbilisi (GMT+4): -240
```

---

### Step 3: Identify the Issue

#### Scenario A: API Response Missing 'Z' Suffix

**Symptom:** `check-timezone-fix.sh` shows timestamp without 'Z'

**Root Cause:** Timezone fix not deployed

**Solution:** Deploy the fix:
```bash
cd /home/wardops/ward-flux-credobank
bash deploy-ui-fixes.sh
```

---

#### Scenario B: Frontend Parsing Issue

**Symptom:**
- API returns correct format with 'Z'
- Browser console shows wrong `Diff hours`

**Root Cause:** Frontend calculation has a bug

**Debug:** Check the actual calculation in [frontend/src/pages/Monitor.tsx:77-95](frontend/src/pages/Monitor.tsx#L77-L95):

```typescript
const downSinceTime = new Date(device.down_since).getTime()
const now = Date.now()
const diff = now - downSinceTime
```

**Possible Issues:**
1. `device.down_since` doesn't have 'Z' (API issue)
2. Browser timezone causing parsing issues
3. Caching old data without 'Z'

**Solution:** Clear browser cache and hard refresh (Ctrl+Shift+R)

---

#### Scenario C: Caching Issue

**Symptom:**
- API returns correct timestamp with 'Z'
- Browser console shows old timestamp without 'Z'

**Root Cause:** Browser caching old API response

**Solution:**
1. Clear Redis cache on server:
```bash
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB
```

2. Hard refresh browser (Ctrl+Shift+R) or clear browser cache

---

#### Scenario D: Race Condition

**Symptom:**
- Sometimes shows correct time
- Sometimes shows wrong time
- Resets when navigating between pages

**Root Cause:** Multiple data sources (database vs VictoriaMetrics)

**Check:** Look at the API code in [routers/devices_standalone.py:131-157](routers/devices_standalone.py#L131-L157)

Should be using `device.down_since` as source of truth:
```python
if obj.down_since is not None:
    ping_status = "Down"
```

NOT using VictoriaMetrics data for status determination.

---

## Fix Priority

### Critical Fixes (Already Applied):

1. ✅ **Device Status Source of Truth** (commit e123567)
   - Changed API to use `device.down_since` instead of VictoriaMetrics
   - File: `routers/devices_standalone.py` lines 131-157

2. ✅ **Timezone Indicator** (commit ad62423)
   - Append 'Z' to timestamp to indicate UTC
   - File: `routers/devices_standalone.py` line 187

3. ✅ **Settings Page Error Messages** (commit d7b252b)
   - Added error handling to Settings user modals
   - File: `frontend/src/pages/Settings.tsx`

### Deployment Status:

- **Fix #1 (Device Status):** ✅ Deployed, working
- **Fix #2 (Settings Errors):** ⚠️ Needs deployment
- **Fix #3 (Timezone):** ⚠️ Needs verification

---

## Testing After Deployment

### Test 1: Verify Timezone Fix

```bash
# On server
cd /home/wardops/ward-flux-credobank
bash check-timezone-fix.sh
```

Expected: `✅ TIMEZONE FIX DEPLOYED - timestamp has Z suffix`

---

### Test 2: Verify Downtime Calculation

1. Open UI: http://10.30.25.46:5001/monitor
2. Find device 10.195.5.17
3. Note the downtime shown (e.g., "17m")
4. Open browser console (F12)
5. Look for debug output:
   ```
   [PING-RuckusAP-AP_10.195.5.17] down_since: 2025-10-24T16:03:52.052638Z
   Diff hours: 0.28
   ```
6. Calculate expected: `0.28 hours × 60 = ~17 minutes` ✅
7. Refresh page (F5)
8. Downtime should increase by ~1 minute (not reset)
9. Navigate to Settings page
10. Navigate back to Monitor page
11. Downtime should still be correct (not reset)

---

### Test 3: Compare with Database

```bash
# On server - get database timestamp
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT name, ip, down_since, NOW() - down_since as actual_downtime FROM standalone_devices WHERE ip = '10.195.5.17';"
```

Example output:
```
             name             |     ip      |        down_since          | actual_downtime
------------------------------+-------------+----------------------------+------------------
 PING-RuckusAP-AP_10.195.5.17 | 10.195.5.17 | 2025-10-24 16:03:52.052638 | 00:17:23.456789
```

UI should show: "Down 17m" ✅

---

## Common Issues and Solutions

### Issue 1: Still showing wrong time after deployment

**Cause:** Browser cache or Redis cache

**Solution:**
```bash
# Clear Redis
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB

# Hard refresh browser: Ctrl+Shift+R
# Or clear browser cache: DevTools → Application → Clear storage
```

---

### Issue 2: Downtime resets when navigating

**Cause:** API returning different values on each request

**Debug:**
1. Open browser Network tab (F12 → Network)
2. Navigate to Monitor page
3. Find request to `/api/v1/devices/standalone/list`
4. Check response, look for `down_since` value
5. Navigate away and back
6. Check if `down_since` value changed

**If value changes:** Monitoring worker is resetting it (bug in state transition logic)

**Solution:** Check worker logs:
```bash
docker logs wardops-worker-prod --tail 100 | grep "10.195.5.17"
```

Look for state transition messages like:
```
✅ Device ... RECOVERED
❌ Device ... went DOWN
```

---

### Issue 3: Timezone offset error (4 hours wrong)

**Cause:** Browser parsing timestamp without 'Z' as local time

**Symptom:**
- Database: 16:03 UTC
- Browser parses as: 16:03 Tbilisi (should be 20:03 Tbilisi)
- Difference: 4 hours (exactly the GMT+4 offset)

**Solution:** Deploy timezone fix (adds 'Z' suffix)

---

## Summary Checklist

Before considering this issue resolved:

- [ ] Timezone fix deployed (`bash deploy-ui-fixes.sh`)
- [ ] API returns timestamps with 'Z' suffix (`bash check-timezone-fix.sh`)
- [ ] Redis cache cleared
- [ ] Browser cache cleared (Ctrl+Shift+R)
- [ ] Device shows correct downtime in UI
- [ ] Browser console shows correct `Diff hours`
- [ ] Downtime doesn't reset on page refresh
- [ ] Downtime doesn't reset when navigating
- [ ] Downtime matches database calculation

---

## Contact

If issue persists after all steps:

1. Capture browser console output (all the debug logs)
2. Capture API response from Network tab
3. Capture database timestamp
4. Note the exact time difference between expected and actual
5. Check for 4-hour offset (indicates timezone issue)

This will help identify if it's:
- API issue (wrong format)
- Frontend issue (wrong calculation)
- Caching issue (stale data)
- Monitoring worker issue (resetting timestamp)
