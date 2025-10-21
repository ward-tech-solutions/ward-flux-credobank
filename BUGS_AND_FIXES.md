# 🐛 Bugs Found & Fixes

## Bug 1: Time Display Not Updating in Real-Time

**What you see:**
- "Down < 2m • RECENT" doesn't change until page refreshes

**Root cause:**
- Time display only updates when API data refetches (every 30 seconds)
- Not a real-time ticking counter

**Is this a bug?**
- **NO** - This is intentional design to avoid constant re-renders
- The display updates every 30 seconds (watch the countdown timer)

**How to verify it's working:**
1. Note a device showing "Down < 2m"
2. Wait for the refresh countdown (top right) to hit 0
3. After refresh, it will show "Down 3m" or "Down 4m"

**If you want real-time ticking**, we need to add a React state update timer.

---

## Bug 2: Add Device Form Styling Issues

**What you see:**
- Form has dark background
- Labels might be hard to read
- No clear field separation

**Root cause:**
- Dark mode theme applied
- Modal background might need better contrast

**To check on server:**
```bash
# Verify frontend build is latest
docker exec wardops-api-prod ls -la /app/static/index*.js
```

**Potential fixes:**
1. Add better contrast to form labels
2. Add field borders/separators
3. Improve modal background

---

## Bug 3: No Visual Indicator for SNMP vs ICMP Monitoring

**What you see:**
- All devices look the same
- Can't tell which devices have SNMP enabled

**Root cause:**
- No badge/icon showing monitoring type

**How devices are monitored:**
- **ICMP only**: Device has no `snmp_community` set → Ping monitoring only
- **ICMP + SNMP**: Device has `snmp_community` set → Ping + SNMP data collection

**Check device monitoring type on server:**
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
  hostname,
  ip,
  device_type,
  CASE
    WHEN snmp_community IS NULL OR snmp_community = '' THEN 'ICMP Only'
    ELSE 'ICMP + SNMP'
  END as monitoring_type,
  snmp_version,
  ping_status
FROM devices
ORDER BY id
LIMIT 20;
"
```

**Suggested fix:**
Add a badge to each device card showing:
- 📡 "SNMP" badge (green) - if SNMP community is set
- 📶 "ICMP" badge (blue) - if only ping monitoring

---

## Verification Commands (Run on CredoBank Server)

### 1. Check if SNMP Polling is Working

```bash
# Check worker logs for SNMP activity
docker logs wardops-worker-prod 2>&1 | grep -i "snmp\|polling" | tail -50

# Check for SNMP errors
docker logs wardops-worker-prod 2>&1 | grep -i "error\|failed" | tail -20
```

### 2. Check Database for SNMP Data

```bash
# See which devices have SNMP configured
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
  hostname,
  device_type,
  snmp_community,
  snmp_version,
  ping_status,
  COUNT(*) OVER() as total_devices
FROM devices
WHERE snmp_community IS NOT NULL AND snmp_community != ''
LIMIT 10;
"

# Check if health checks are being recorded
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
  COUNT(*) as total_health_checks,
  COUNT(DISTINCT device_id) as unique_devices,
  MIN(created_at) as earliest_check,
  MAX(created_at) as latest_check
FROM device_health_checks;
"
```

### 3. Check Monitoring Mode

```bash
# Verify monitoring mode setting
docker exec wardops-api-prod env | grep MONITORING_MODE
# Should show: MONITORING_MODE=snmp_only

# Check celery worker concurrency
docker exec wardops-api-prod env | grep CELERY_WORKER_CONCURRENCY
# Should show: CELERY_WORKER_CONCURRENCY=60
```

### 4. Check Celery Tasks

```bash
# View active celery tasks
docker exec wardops-worker-prod celery -A celery_app inspect active

# View scheduled tasks
docker exec wardops-worker-prod celery -A celery_app inspect scheduled

# View worker stats
docker exec wardops-worker-prod celery -A celery_app inspect stats
```

---

## Expected Behavior

### For SNMP-enabled devices (e.g., Cisco switches):
- ✅ ICMP (ping) checks every 60 seconds
- ✅ SNMP polling for interface status, bandwidth, errors
- ✅ Device type auto-detection from SNMP sysDescr
- ✅ Interface statistics collection
- ✅ Health status based on both ping and SNMP

### For ICMP-only devices (e.g., PayBoxes, ATMs):
- ✅ ICMP (ping) checks every 60 seconds
- ❌ No SNMP data collection
- ✅ Health status based on ping only

---

## Quick Fixes Needed

1. **Add monitoring type badge** to device cards
2. **Improve Add Device form contrast** in dark mode
3. **Add real-time countdown** for device downtime (optional)
4. **Add SNMP status indicator** showing if SNMP is responding

Let me know which bug you want me to fix first!
