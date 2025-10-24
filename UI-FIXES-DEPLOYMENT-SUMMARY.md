# UI Fixes Deployment Summary

## Overview

Three critical UI fixes have been committed to the repository and need to be deployed to the Credobank production server.

**Repository:** ward-ops-credobank
**Branch:** main
**Server:** 10.30.25.46 (Flux server at Credobank)
**Date:** 2025-10-24

---

## Fixes Included

### Fix #1: Device Status Display Bug ✅ DEPLOYED

**Commit:** e123567
**Status:** Already deployed and working
**File:** `routers/devices_standalone.py`

**Problem:**
- Device showing UP (green) in monitor grid when actually DOWN
- Zabbix correctly alerting device is down
- Detail view showing correct "Down" status
- **Root cause:** API using VictoriaMetrics data instead of `device.down_since`

**Solution:**
Changed API to use `device.down_since` as the authoritative source of truth for device status.

```python
# BEFORE: Used VictoriaMetrics ping data (could be stale)
# AFTER: Use device.down_since field (always current)
if obj.down_since is not None:
    ping_status = "Down"
    available = "Unavailable"
else:
    ping_status = "Up"
    available = "Available"
```

**Result:** Device now correctly shows RED "Down" status in both grid and detail views.

---

### Fix #2: Settings Page Error Messages ⚠️ NEEDS DEPLOYMENT

**Commit:** d7b252b
**Status:** Needs deployment
**File:** `frontend/src/pages/Settings.tsx`

**Problem:**
- User tries to create duplicate username in Settings page
- Backend returns HTTP 400 "Username already registered"
- Frontend shows no error message to user

**Solution:**
Added error handling to Settings page user management modals (matching the Users page pattern).

Changes:
1. Added `errorMessage` state
2. Updated `handleAddUser()` with try-catch
3. Updated `handleEditUser()` with try-catch
4. Added error alert UI component
5. Clear errors when closing modal

**Result:** Users will see clear error messages when trying to create duplicate usernames/emails.

---

### Fix #3: Timezone Bug in Downtime Calculation ⚠️ NEEDS VERIFICATION

**Commit:** ad62423
**Status:** Deployed but needs verification
**File:** `routers/devices_standalone.py`

**Problem:**
- Device downtime showing "Down 11m" when should show "Down 17m"
- Downtime resets when refreshing page or navigating
- **Root cause:** API returning timestamp without timezone indicator

**Example:**
```json
❌ BEFORE: "down_since": "2025-10-24T16:03:52.052638"
✅ AFTER:  "down_since": "2025-10-24T16:03:52.052638Z"
```

Without the 'Z' suffix, JavaScript's `new Date()` parses the timestamp as **local time** (Tbilisi GMT+4) instead of **UTC**, causing a 4-hour offset in calculations.

**Solution:**
Append 'Z' to timestamp in API response:

```python
# BEFORE:
'down_since': obj.down_since.isoformat() if obj.down_since else None,

# AFTER:
'down_since': obj.down_since.isoformat() + 'Z' if obj.down_since else None,
```

**Result:** Downtime calculation should be accurate and consistent.

---

## Deployment Instructions

### Option 1: Deploy All Fixes (Recommended)

Run this single command on the Credobank server:

```bash
cd /home/wardops/ward-flux-credobank
bash deploy-ui-fixes.sh
```

This script will:
1. Pull latest code from GitHub
2. Rebuild API container (includes frontend build)
3. Restart API container
4. Clear Redis cache
5. Verify deployment

**Time:** ~3-5 minutes

---

### Option 2: Manual Deployment

If you prefer to deploy manually:

```bash
# 1. Navigate to project directory
cd /home/wardops/ward-flux-credobank

# 2. Pull latest code
git pull origin main

# 3. Rebuild API container
docker-compose -f docker-compose.production-priority-queues.yml build api

# 4. Stop API container
docker-compose -f docker-compose.production-priority-queues.yml stop api

# 5. Remove old container
docker ps -a | grep api | grep Exited | awk '{print $1}' | xargs docker rm

# 6. Start new container
docker-compose -f docker-compose.production-priority-queues.yml up -d api

# 7. Wait for startup
sleep 15

# 8. Clear Redis cache
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB

# 9. Verify API is running
docker ps | grep api
curl http://localhost:5001/api/v1/health
```

---

## Verification Steps

### Step 1: Check Timezone Fix Deployment

```bash
cd /home/wardops/ward-flux-credobank
bash check-timezone-fix.sh
```

**Expected:**
```
✅ TIMEZONE FIX DEPLOYED - timestamp has Z suffix
down_since: 2025-10-24T16:03:52.052638Z
```

---

### Step 2: Test Device Status Display (Fix #1)

1. Open: http://10.30.25.46:5001/monitor
2. Search for device: `10.195.5.17` (RuckusAP-AP)
3. **Verify:** Shows RED "Down" indicator (not green)
4. Click on the device to view details
5. **Verify:** Detail view also shows "Down - Not responding"

**Expected:** Both grid and detail views consistently show DOWN status

---

### Step 3: Test Settings Error Messages (Fix #2)

1. Open: http://10.30.25.46:5001/settings
2. Scroll to "User Management" section
3. Click "Add New User" button
4. Enter username: `admin` (existing user)
5. Fill other required fields
6. Click "Add User"
7. **Verify:** RED error box appears with message "Username already registered"
8. Click X button on error box
9. **Verify:** Error disappears

**Expected:** Clear error messages for duplicate username/email attempts

---

### Step 4: Test Downtime Calculation (Fix #3)

#### Part A: Visual Check

1. Open: http://10.30.25.46:5001/monitor
2. Find device `10.195.5.17` (should be DOWN)
3. Note the downtime displayed (e.g., "17m")
4. Wait 1 minute
5. Refresh page (F5)
6. **Verify:** Downtime increased by ~1 minute (didn't reset)
7. Navigate to Settings page
8. Navigate back to Monitor page
9. **Verify:** Downtime still correct (didn't reset)

#### Part B: Console Debug Check

1. Keep Monitor page open
2. Press F12 to open DevTools
3. Click "Console" tab
4. Look for debug output:
   ```
   [PING-RuckusAP-AP_10.195.5.17] down_since: 2025-10-24T16:03:52.052638Z
   Date: 2025-10-24T16:03:52.052Z
   Diff hours: 0.28
   ```
5. **Verify:** `down_since` has 'Z' at the end
6. **Verify:** `Diff hours` matches actual elapsed time

#### Part C: Database Comparison

Run this on the server:

```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT name, ip, down_since, NOW() - down_since as actual_downtime FROM standalone_devices WHERE ip = '10.195.5.17';"
```

Example output:
```
             name             |     ip      |        down_since          | actual_downtime
------------------------------+-------------+----------------------------+------------------
 PING-RuckusAP-AP_10.195.5.17 | 10.195.5.17 | 2025-10-24 16:03:52.052638 | 00:17:23.456789
```

**Verify:** UI downtime matches database `actual_downtime` (within 1 minute)

---

## Troubleshooting

### Issue: Timezone fix shows not deployed

**Solution:** Deploy the fixes:
```bash
cd /home/wardops/ward-flux-credobank
bash deploy-ui-fixes.sh
```

---

### Issue: Downtime still incorrect after deployment

**Possible causes:**
1. Browser cache showing old data
2. Redis cache not cleared
3. API container not restarted properly

**Solutions:**

```bash
# Clear Redis cache
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB

# Clear browser cache
# In browser: Ctrl+Shift+R (hard refresh)
# Or: DevTools → Application → Clear storage → Clear site data

# Verify API container is new
docker ps --format "{{.Names}}\t{{.CreatedAt}}" | grep api
# Should show recent creation time
```

---

### Issue: Still showing wrong downtime (4 hours off)

**Diagnosis:** This indicates timezone parsing issue (GMT+4 offset)

**Root cause:** Browser parsing timestamp without 'Z' as local time

**Solution:**
1. Verify timezone fix is deployed:
   ```bash
   bash check-timezone-fix.sh
   ```
2. If shows "NOT DEPLOYED", run deployment again
3. Clear Redis and browser cache
4. Hard refresh (Ctrl+Shift+R)

---

### Issue: Error messages not showing in Settings

**Possible causes:**
1. Frontend not rebuilt
2. Browser caching old JavaScript

**Solutions:**

```bash
# Rebuild API container (includes frontend)
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker-compose -f docker-compose.production-priority-queues.yml up -d api

# Clear browser cache completely
# DevTools → Application → Clear storage → Clear site data
```

---

## Files Reference

**Created files for deployment:**

1. **deploy-ui-fixes.sh** - Main deployment script
   - Pulls latest code
   - Rebuilds API container
   - Restarts container
   - Clears Redis cache
   - Verifies deployment

2. **check-timezone-fix.sh** - Verification script
   - Checks API response format
   - Verifies 'Z' suffix on timestamps
   - Shows current server time

3. **DOWNTIME-CALCULATION-DEBUG.md** - Detailed debugging guide
   - Root cause analysis
   - Step-by-step debugging
   - Browser console commands
   - Common issues and solutions

4. **UI-FIXES-DEPLOYMENT-SUMMARY.md** - This document
   - Overview of all fixes
   - Deployment instructions
   - Verification steps
   - Troubleshooting guide

---

## Deployment Checklist

Before deployment:
- [ ] SSH access to server (10.30.25.46)
- [ ] Git repository is on `main` branch
- [ ] No uncommitted changes
- [ ] All commits pushed to GitHub

During deployment:
- [ ] Run `deploy-ui-fixes.sh` script
- [ ] Wait for container rebuild (2-3 minutes)
- [ ] Verify API container is running
- [ ] Verify health check passes
- [ ] Redis cache cleared

After deployment:
- [ ] Verify timezone fix deployed (`check-timezone-fix.sh`)
- [ ] Test device status display (Fix #1)
- [ ] Test Settings error messages (Fix #2)
- [ ] Test downtime calculation (Fix #3)
- [ ] Monitor logs for errors
- [ ] Check memory usage is stable

---

## Expected Timeline

| Step | Duration | Status |
|------|----------|--------|
| Pull code | 10 seconds | - |
| Build API container | 2-3 minutes | - |
| Restart container | 20 seconds | - |
| Wait for startup | 15 seconds | - |
| Clear cache | 5 seconds | - |
| Verification | 2-3 minutes | - |
| **Total** | **~5-8 minutes** | - |

---

## Success Criteria

All three fixes working correctly:

✅ **Fix #1 - Device Status:**
- Devices showing DOWN have RED indicator (not green)
- Status consistent between grid view and detail view
- Status matches Zabbix alerts

✅ **Fix #2 - Settings Errors:**
- Error messages appear for duplicate username
- Error messages appear for duplicate email
- Errors can be dismissed with X button
- Errors clear when closing modal

✅ **Fix #3 - Downtime Calculation:**
- Downtime shows correct duration (matches database)
- Downtime doesn't reset on page refresh
- Downtime doesn't reset when navigating
- Timestamps have 'Z' suffix in API response
- Browser console shows correct calculation

---

## Post-Deployment Monitoring

Monitor these for 10-15 minutes after deployment:

### 1. API Logs
```bash
docker logs wardops-api-prod -f --tail 50
```

Look for:
- ✅ No errors or exceptions
- ✅ Successful API requests
- ✅ Health check responses

### 2. Memory Usage
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

Should be stable:
- API: ~500MB-1GB
- Workers: ~1-2GB
- Redis: <500MB

### 3. Active Connections
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \
  "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"
```

Should see:
- Active: 5-15 connections
- Idle: 10-30 connections
- Idle in transaction: <5 connections

---

## Rollback Plan

If deployment causes issues:

```bash
# 1. Check previous commit
git log --oneline -10

# 2. Rollback to previous version
git checkout <previous_commit_hash>

# 3. Rebuild and restart
docker-compose -f docker-compose.production-priority-queues.yml build api
docker-compose -f docker-compose.production-priority-queues.yml up -d api

# 4. Clear cache
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB
```

Then investigate the issue before re-deploying.

---

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review logs: `docker logs wardops-api-prod --tail 100`
3. Review the detailed debug guide: `DOWNTIME-CALCULATION-DEBUG.md`
4. Verify timezone fix: `bash check-timezone-fix.sh`

For persistent issues, gather:
- Browser console output (F12 → Console)
- Network tab showing API responses (F12 → Network)
- Database timestamp query results
- Container logs

---

## Summary

Three fixes are ready to deploy:

1. **Device Status** (e123567) - ✅ Already deployed, working
2. **Settings Errors** (d7b252b) - ⚠️ Needs deployment
3. **Timezone Fix** (ad62423) - ⚠️ Needs deployment + verification

**Action Required:**
```bash
cd /home/wardops/ward-flux-credobank
bash deploy-ui-fixes.sh
```

Then verify all three fixes are working as expected.
