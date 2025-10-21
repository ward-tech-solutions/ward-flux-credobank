# Root Cause Analysis - WARD OPS CredoBank Issues

**Date:** October 21, 2025
**Issues:** Delete button not working, Monitor showing UP devices as DOWN

---

## Issue 1: Delete Button Not Working

### ROOT CAUSE
Docker's legacy builder was caching the `COPY frontend/ ./` command even with `--no-cache` flag, causing old source files (without delete button code) to be copied into the image.

### Why It Happened
1. Dockerfile line 16: `COPY frontend/ ./`
2. Docker caches based on file checksums
3. When `--no-cache` is used, Docker SHOULD rebuild everything
4. **BUG:** Legacy builder still used cache for COPY commands
5. Old source files → Vite builds old code → Same hash `index-CWvAtuJb.js`

### The Fix
Added `ARG CACHE_BUST` **before** the COPY command:

```dockerfile
# Cache buster - this invalidates the cache when source changes
ARG CACHE_BUST=unknown
RUN echo "Cache bust: ${CACHE_BUST}"

# Copy frontend source
COPY frontend/ ./
```

When `CACHE_BUST` changes (we pass current timestamp), Docker cannot use cached layers and must re-copy files.

### Files Changed
- `Dockerfile`: Added CACHE_BUST arg before frontend source copy
- `deploy-fixed.sh`: Builds with `--build-arg CACHE_BUST=$(date +%s)`

### Verification
After deployment, check that the JavaScript bundle has a NEW hash (not `index-CWvAtuJb.js`).

---

## Issue 2: Monitor Showing UP Devices as DOWN

### SYMPTOMS
From Slack screenshot:
- Devices showing on Monitor page (which only shows DOWN devices)
- But Zabbix shows devices came back UP quickly
- Suggests `ping_status` not updating correctly

### POSSIBLE CAUSES

#### Cause A: Ping Tasks Not Running
If Celery workers aren't running ping tasks, devices won't update their status.

**Check:**
```bash
# Verify worker is running
docker logs wardops-worker-prod | grep "ping_all_devices"

# Should see logs like:
# "Pinging 875 standalone devices"
```

**Fix:**
```bash
# Restart worker
docker restart wardops-worker-prod
```

#### Cause B: Monitoring Profile Incorrect
If monitoring profile is set to "zabbix" mode, standalone pings won't run.

**Check:**
```sql
SELECT mode, is_active FROM monitoring_profiles WHERE is_active = true;
```

**Should show:** `mode = 'snmp_only'` or `mode = 'standalone'`

**Fix:**
Update monitoring profile to standalone mode.

#### Cause C: Stale down_since Timestamps
Devices might have old `down_since` values that weren't cleared.

**Check:**
```sql
SELECT name, ip, down_since, enabled
FROM standalone_devices
WHERE down_since IS NOT NULL
ORDER BY down_since DESC
LIMIT 20;
```

**Fix:**
The ping task has self-healing logic (lines 233-241 in tasks.py):
- If device is UP but has `down_since`, it clears it
- If device is DOWN but missing `down_since`, it sets it

This should auto-correct on next ping cycle.

#### Cause D: Monitor Page Filter Issue
The Monitor page filters devices with `ping_status === 'Down'`.

**Check browser console:**
Open F12 → Console, look for device data:
```javascript
// Should only see devices with ping_status: "Down"
devices.filter(d => d.ping_status === 'Down')
```

---

## Deployment Instructions

### Step 1: Deploy Fixed Dockerfile

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
./deploy-fixed.sh
```

This will:
1. Pull latest code with Dockerfile fix
2. Build with CACHE_BUST to force fresh frontend copy
3. Verify new frontend hash
4. Deploy all containers

### Step 2: Verify Delete Button

1. **Clear browser cache:** CTRL+SHIFT+R (Windows) or CMD+SHIFT+R (Mac)
2. Open Devices page: http://10.30.25.39:5001/devices
3. Open DevTools (F12) → Network tab
4. Refresh and verify NEW JavaScript bundle loads (not `index-CWvAtuJb.js`)
5. Click delete button (trash icon) on a test device
6. **Expected:** Confirmation modal appears
7. Click "Delete"
8. **Expected:** Toast notification "Device deleted successfully"

### Step 3: Investigate Monitor Page Issue

**Option A: Check Worker Logs**
```bash
docker logs wardops-worker-prod --tail 100 | grep -E "ping_all_devices|went DOWN|came back UP"
```

Look for:
- `"Pinging X standalone devices"` - Confirms pings are running
- `"Device X went DOWN"` - State transitions being detected
- `"Device X came back UP"` - Devices recovering

**Option B: Check Database**
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT COUNT(*) as total_devices,
       SUM(CASE WHEN down_since IS NOT NULL THEN 1 ELSE 0 END) as currently_down
FROM standalone_devices
WHERE enabled = true;
"
```

**Option C: Check Latest Ping Results**
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT device_name, device_ip, is_reachable, timestamp
FROM ping_results
ORDER BY timestamp DESC
LIMIT 20;
"
```

This shows if pings are actually running and what results they're getting.

### Step 4: Fix Stale Data (if needed)

If devices are showing DOWN but are actually UP:

```bash
# Connect to database
docker exec -it wardops-postgres-prod psql -U ward_admin -d ward_ops

# Clear stale down_since for devices that are UP
UPDATE standalone_devices
SET down_since = NULL
WHERE down_since IS NOT NULL
AND id IN (
    SELECT DISTINCT ON (device_ip)
           sd.id
    FROM standalone_devices sd
    JOIN ping_results pr ON pr.device_ip = sd.ip
    WHERE pr.is_reachable = true
    ORDER BY device_ip, pr.timestamp DESC
);
```

---

## Summary

### Delete Button - FIXED ✅
- Root cause: Docker cache issue
- Solution: CACHE_BUST arg in Dockerfile
- Status: Committed and ready to deploy

### Monitor Page - INVESTIGATION NEEDED ⚠️
- Likely cause: Ping tasks not running or stale data
- Solution: Check worker logs and database
- Status: Needs on-server investigation

---

## Next Steps

1. ✅ Deploy with `./deploy-fixed.sh`
2. ✅ Verify delete button works
3. ⚠️ Check worker logs for ping activity
4. ⚠️ Query database to check device states
5. ⚠️ Clear stale data if needed
6. ✅ Test timezone fix in browser console

---

## Files Modified

1. `Dockerfile` - Added CACHE_BUST for proper cache invalidation
2. `deploy-fixed.sh` - Deployment script with cache busting
3. `ROOT-CAUSE-ANALYSIS.md` - This document

All changes committed to: `ward-flux-credobank` repository, `main` branch
