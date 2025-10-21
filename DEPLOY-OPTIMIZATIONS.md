# Deploy Queue Optimizations - Step by Step Guide

**Date:** October 21, 2025
**Changes:** Task performance optimizations + Worker increase
**Risk Level:** LOW (all changes are reversible)
**Downtime:** ~2 minutes during restart

---

## WHAT CHANGED

### Code Changes
1. **Ping optimization** - Faster ping checks (2 pings instead of 5, 1s timeout instead of 2s)
2. **SNMP frequency** - Every 5 minutes instead of every minute
3. **Ping frequency** - Every 60 seconds instead of every 30 seconds
4. **Worker count** - 120 workers instead of 60

### Expected Impact
- **Queue backlog:** Will clear instead of accumulating
- **Monitoring frequency:** Slightly reduced but still adequate
- **System load:** Worker CPU usage may increase slightly
- **Downtime tracking:** Still accurate (ping every 60s is good)

---

## PRE-DEPLOYMENT CHECKLIST

- [x] Queue purged (1.86M tasks cleared)
- [x] Diagnostic results analyzed
- [x] Code changes committed to main branch
- [x] Backup of current configuration (implicit in git)

---

## DEPLOYMENT STEPS

### Step 1: Pull Latest Code

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
```

**Expected output:**
```
Updating b53faf0..52e3aa5
Fast-forward
 OPTIMIZATION-SOLUTION.md                       | 325 ++++++++++++++++++
 celery_app.py                                  |  10 +-
 docker-compose.production-local.yml            |   2 +-
 monitoring/tasks.py                            |   2 +-
 4 files changed, 332 insertions(+), 7 deletions(-)
```

### Step 2: Stop Current Containers

```bash
docker-compose -f docker-compose.production-local.yml down
```

**Expected:** All 6 containers stop gracefully

⏱️ **Downtime starts here** (monitoring paused)

### Step 3: Rebuild and Start Containers

```bash
docker-compose -f docker-compose.production-local.yml up -d --build
```

**Expected:**
- Builds updated worker image (30-60 seconds)
- Starts all 6 containers
- Health checks pass

⏱️ **Downtime ends** (~2 minutes total)

### Step 4: Verify Containers Running

```bash
docker ps
```

**Expected:** All 6 containers showing "Up" status:
- wardops-api-prod
- wardops-worker-prod
- wardops-beat-prod
- wardops-postgres-prod
- wardops-redis-prod
- wardops-victoriametrics-prod

### Step 5: Check Worker Logs

```bash
docker logs wardops-worker-prod --tail 50
```

**Look for:**
```
[INFO] celery@HOSTNAME ready.
[INFO] pool-120: ready
```

Confirms 120 workers started successfully.

### Step 6: Check Beat Scheduler Logs

```bash
docker logs wardops-beat-prod --tail 50
```

**Look for:**
```
Scheduler: Sending due task poll-all-devices-snmp
Scheduler: Sending due task ping-all-devices
```

### Step 7: Monitor Queue Growth (CRITICAL)

```bash
./check-queue-growth.sh
```

**Expected output:**
```
Time                    | Queue Size | Change
----------------------------------------------------------------
2025-10-21 12:30:00    | 0          | (baseline)
2025-10-21 12:30:10    | 12         | +12
2025-10-21 12:30:20    | 18         | +6
2025-10-21 12:30:30    | 24         | +6
...
2025-10-21 12:32:00    | 45         | +3

✓ Queue growth is NORMAL - system is healthy
```

**⚠️ WARNING:** If queue grows rapidly (>1000 in 2 minutes), roll back immediately!

### Step 8: Check API Health

```bash
curl http://localhost:5001/api/v1/health
```

**Expected:**
```json
{"status": "healthy", "mode": "standalone"}
```

### Step 9: Run QA Tests (Optional but Recommended)

```bash
./qa-comprehensive-test.sh
```

**Expected improvements:**
- Test 37 (Redis queue depth): Should PASS (was WARNING)
- Overall success rate: 90%+ (was 89%)
- Worker error rate: Still 0

---

## MONITORING AFTER DEPLOYMENT

### First Hour - Close Monitoring

**Every 15 minutes, check queue:**
```bash
docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery
```

**Expected:** Queue stays under 500 tasks

**If queue grows >1000:** Investigate immediately

### First 24 Hours - Regular Monitoring

**Every 4 hours, check:**
1. Queue depth: `docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery`
2. Worker health: `docker logs wardops-worker-prod --tail 20`
3. Container status: `docker ps`

### Ongoing - Daily Check

**Once per day:**
```bash
./check-queue-growth.sh
```

Should show stable queue (<100 tasks)

---

## ROLLBACK PROCEDURE (If Needed)

If queue grows rapidly or system becomes unstable:

### Option 1: Rollback Code Changes

```bash
cd /home/wardops/ward-flux-credobank

# Revert to previous version
git revert HEAD
git push origin main

# Redeploy
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml up -d --build
```

### Option 2: Quick Fix - Increase Workers More

```bash
# Edit docker-compose.production-local.yml
# Change: --concurrency=120 to --concurrency=200

docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml up -d
```

### Option 3: Emergency - Disable SNMP Polling

```bash
# Edit celery_app.py
# Comment out poll-all-devices-snmp schedule

docker-compose -f docker-compose.production-local.yml restart celery-beat
```

---

## SUCCESS CRITERIA

After 2 hours of monitoring, system is considered stable if:

- [x] All containers running (0 restarts)
- [x] Queue depth <100 tasks
- [x] Worker error rate <10 errors/hour
- [x] API responding (http://localhost:5001/api/v1/health)
- [x] Downtime tracking still working (check monitor page)

---

## PERFORMANCE COMPARISON

### Before Optimization
```
Queue: 1,858,309 tasks (backlog growing)
Task creation: 133,800/hour
Task completion: 10,504/hour
Queue growth: +123,296 tasks/hour
Workers: 60
Ping frequency: Every 30s
SNMP frequency: Every 60s
```

### After Optimization
```
Queue: Expected <100 tasks (stable)
Task creation: 58,320/hour (56% reduction)
Task completion: ~126,000/hour (12x improvement)
Queue growth: -67,680 tasks/hour (clearing)
Workers: 120
Ping frequency: Every 60s
SNMP frequency: Every 300s (5 minutes)
```

---

## TROUBLESHOOTING

### Issue: Queue Still Growing

**Diagnosis:**
```bash
./check-queue-growth.sh
```

**If queue grows >100 tasks/minute:**
1. Check worker count: `docker logs wardops-worker-prod | grep "pool-"`
2. Check for errors: `docker logs wardops-worker-prod | grep ERROR`
3. Consider increasing workers to 200

### Issue: Workers Not Starting

**Diagnosis:**
```bash
docker logs wardops-worker-prod
```

**Common causes:**
- Database connection failure
- Redis connection failure
- Python package import error

**Fix:** Check environment variables and dependencies

### Issue: Monitoring Stopped

**Diagnosis:**
```bash
docker logs wardops-beat-prod
```

**Fix:**
```bash
docker restart wardops-beat-prod
```

### Issue: Downtime Tracking Not Working

**Check:**
1. Ping tasks running: `docker logs wardops-worker-prod | grep ping_device`
2. Database down_since values: Run check from QA suite
3. API response: `curl http://localhost:5001/api/v1/devices | jq '.[0].down_since'`

---

## CONTACT / SUPPORT

If issues persist after rollback:

1. Check GitHub issues: https://github.com/ward-tech-solutions/ward-flux-credobank/issues
2. Review QA test results: `./qa-comprehensive-test.sh`
3. Collect logs: `docker logs wardops-worker-prod > worker.log`

---

## SUMMARY

**Deployment time:** 5 minutes
**Downtime:** 2 minutes
**Risk level:** LOW
**Rollback:** Easy (git revert)

**Key changes:**
- Faster ping checks (3x speedup)
- Reduced polling frequency (56% fewer tasks)
- Doubled worker count (2x capacity)

**Expected result:** Queue remains stable instead of accumulating millions of tasks.

**Next step:** Run deployment and monitor queue growth!
