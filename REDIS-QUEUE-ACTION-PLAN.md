# Redis Queue Backlog - Action Plan

**Date:** October 21, 2025
**Priority:** HIGH
**Status:** DIAGNOSED - AWAITING USER DECISION

---

## PROBLEM SUMMARY

**Redis Queue:** 1,859,709 tasks queued (1.86 million!)

**Current State:**
- Workers processing: 19 active tasks
- Worker pool size: 60 concurrent workers
- Tasks completed: 115,544 total (in 11 hours = ~10,500/hour)
- Queue growth rate: Unknown (need monitoring items count)

**Impact:**
- Monitoring delays may occur
- Redis memory usage: 2.04GB (growing)
- Potential system slowdown if queue grows indefinitely

---

## ROOT CAUSE

### Celery Beat Schedule

**Every 30 seconds:**
```python
'ping-all-devices': {
    'task': 'monitoring.tasks.ping_all_devices',
    'schedule': 30.0,
}
# Creates: 876 ping tasks (one per enabled device)
```

**Every 60 seconds:**
```python
'poll-all-devices-snmp': {
    'task': 'monitoring.tasks.poll_all_devices_snmp',
    'schedule': 60.0,
}
# Creates: N tasks (one per device with monitoring items)
```

### The Issue

The `poll_all_devices_snmp` task queries:
```python
devices = db.query(MonitoringItem.device_id).distinct().all()
```

Then queues a task for each distinct device:
```python
for device_id in device_ids:
    poll_device_snmp.delay(device_id)
```

**Question:** How many monitoring items exist?

If there are tens of thousands of monitoring items spread across devices, this would create massive task queues.

**Calculation Example:**
- If 500 devices have monitoring items
- Every 60s: 500 SNMP poll tasks created
- Every 30s: 876 ping tasks created
- Per minute: 500 + (876 × 2) = 2,252 tasks/minute
- Per hour: 135,120 tasks/hour

If workers complete ~10,500 tasks/hour but 135,000 are created, the queue grows by 124,500 tasks/hour.

Over 11 hours: 124,500 × 11 = 1,369,500 tasks (close to our 1.86M!)

---

## IMMEDIATE DIAGNOSTIC REQUIRED

**Before taking action, run:**

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main

# Check monitoring items count
./check-monitoring-items.sh
```

This will show:
1. Total monitoring items in database
2. How many devices have monitoring items
3. Monitoring items per device (top 10)
4. Current monitoring mode (should be snmp_only or standalone)

**Based on results, we'll know:**
- Is this a configuration issue? (too many monitoring items)
- Is this a performance issue? (workers too slow)
- Is this a scheduling issue? (tasks scheduled too frequently)

---

## ACTION OPTIONS

### Option 1: Purge Queue + Optimize (RECOMMENDED)

**Step 1: Purge the backlog**
```bash
./purge-redis-queue.sh
```

⚠️ **WARNING:** This deletes all 1.86M queued tasks

**Step 2: Monitor queue growth**
```bash
watch -n 5 'docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery'
```

**Step 3: If queue grows rapidly again:**
- Reduce polling frequency
- Increase worker count
- Disable SNMP monitoring if not needed

**Pros:**
- Immediate resolution
- Fresh start
- Easy to monitor

**Cons:**
- Loses queued tasks (but they're outdated anyway - monitoring is real-time)
- Doesn't fix root cause

### Option 2: Increase Worker Count

**Current:** 60 workers
**Try:** 120 workers

```bash
# Stop worker container
docker stop wardops-worker-prod

# Edit docker-compose.production-local.yml
# Change: --concurrency=60 to --concurrency=120

# Restart
docker start wardops-worker-prod
```

**Pros:**
- Processes tasks faster
- May clear backlog over time
- No data loss

**Cons:**
- Increased CPU/memory usage
- May not solve problem if tasks created faster than processed
- Takes time to clear 1.86M backlog

### Option 3: Reduce Polling Frequency

Edit [celery_app.py](celery_app.py) beat schedule:

```python
# BEFORE
'poll-all-devices-snmp': {
    'task': 'monitoring.tasks.poll_all_devices_snmp',
    'schedule': 60.0,  # Every 60 seconds
},
'ping-all-devices': {
    'task': 'monitoring.tasks.ping_all_devices',
    'schedule': 30.0,  # Every 30 seconds
},

# AFTER
'poll-all-devices-snmp': {
    'task': 'monitoring.tasks.poll_all_devices_snmp',
    'schedule': 300.0,  # Every 5 minutes
},
'ping-all-devices': {
    'task': 'monitoring.tasks.ping_all_devices',
    'schedule': 60.0,  # Every 60 seconds (instead of 30)
},
```

**Pros:**
- Reduces task creation rate
- Sustainable long-term
- Lower system load

**Cons:**
- Slower monitoring updates
- Still need to purge existing backlog
- Requires code change + deployment

### Option 4: Disable SNMP Monitoring (If Not Needed)

Check monitoring profile mode:
```bash
./check-monitoring-items.sh
```

If monitoring_mode is NOT "snmp_only", you might not need SNMP polling at all.

**If only ping monitoring is needed:**
```python
# Comment out in celery_app.py
# 'poll-all-devices-snmp': {
#     'task': 'monitoring.tasks.poll_all_devices_snmp',
#     'schedule': 60.0,
# },
```

**Pros:**
- Eliminates major source of tasks
- Reduces system load significantly
- Ping monitoring still works (downtime tracking)

**Cons:**
- Loses SNMP metrics (CPU, memory, bandwidth, etc.)
- Only suitable if SNMP not required

---

## RECOMMENDED APPROACH

### Phase 1: Diagnose (NOW)
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
./check-monitoring-items.sh
```

### Phase 2: Immediate Relief (TODAY)
```bash
# Purge the backlog
./purge-redis-queue.sh

# Monitor queue growth for 5 minutes
watch -n 5 'docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery'
```

### Phase 3: Optimize Based on Diagnostics

**If monitoring_items count is very high (>10,000):**
- Consider if all monitoring items are needed
- May need to reduce monitored OIDs per device
- Increase worker count to 120

**If monitoring_items count is reasonable (<5,000):**
- Issue is likely worker performance
- Increase worker count to 120
- Consider adding task time limits

**If SNMP monitoring not needed:**
- Disable SNMP polling tasks
- Keep only ping monitoring (sufficient for downtime tracking)

### Phase 4: Long-term Solution

1. **Add queue depth monitoring:**
   ```python
   # In monitoring/tasks.py
   @shared_task(name="monitoring.tasks.report_queue_depth")
   def report_queue_depth():
       import redis
       r = redis.from_url(REDIS_URL)
       queue_depth = r.llen('celery')
       logger.warning(f"Queue depth: {queue_depth}")
       if queue_depth > 10000:
           logger.error(f"CRITICAL: Queue backlog {queue_depth} tasks!")
   ```

2. **Adjust polling frequencies** based on system capacity

3. **Add alerts** for queue depth > threshold

4. **Monitor worker performance** - add metrics to VictoriaMetrics

---

## DECISION MATRIX

| Monitoring Items Count | Recommendation |
|------------------------|----------------|
| < 1,000 items | Purge queue + Increase workers to 120 |
| 1,000 - 5,000 items | Purge + Increase workers + Reduce ping to 60s |
| 5,000 - 10,000 items | Purge + Increase workers to 120 + SNMP to 5min |
| > 10,000 items | Review monitoring strategy - too many items |

**If SNMP metrics not needed:**
- Disable SNMP polling entirely
- Keep only ping monitoring (sufficient for downtime tracking)

---

## TESTING AFTER CHANGES

After implementing solution, run QA suite:
```bash
./qa-comprehensive-test.sh
```

Expected improvements:
- Redis queue depth: <100 tasks (was 1.86M)
- Test 37 should PASS instead of WARN
- System performance may improve

---

## FILES PROVIDED

1. **check-monitoring-items.sh** - Diagnose monitoring items count
2. **purge-redis-queue.sh** - Clear the 1.86M task backlog
3. **check-duplicate-ips.sh** - Fixed duplicate IP checker
4. **diagnose-redis-queue.sh** - Already run, confirmed 1.86M backlog

---

## NEXT STEPS

**Right now, please run:**
```bash
cd /home/wardops/ward-flux-credobank
git pull origin main
./check-monitoring-items.sh
```

**Then share the output so I can:**
1. Determine exact root cause
2. Recommend specific optimization
3. Calculate optimal worker count
4. Decide if SNMP polling should be disabled

After diagnosis, we'll execute the purge and optimization in one operation.

---

## CRITICAL NOTES

1. **Downtime tracking still works** - The ping tasks are being processed (813 tasks/5min confirmed)
2. **System is functional** - Just has backlog of old tasks
3. **No immediate danger** - Redis has plenty of memory (2.04GB used)
4. **Purging is safe** - Tasks are point-in-time monitoring checks, old ones are irrelevant

The 1.86M queued tasks are mostly outdated monitoring checks from hours/days ago. Purging them won't affect current monitoring functionality.
