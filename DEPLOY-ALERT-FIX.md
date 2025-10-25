# Deploy Alert Delay Fix - Production Instructions

**Issue**: 5-minute delay in device down detection
**Fix**: Code now matches working Beat schedule (batched tasks @ 10s interval)
**Status**: ✅ **BATCHED TASKS ALREADY WORKING** - Just need to update code file

---

## Current Status (From Diagnostics)

✅ **Beat IS using batched schedule** (from cached database)
✅ **Workers ARE executing batched tasks correctly**
✅ **9 batches processing 874 devices in ~3 seconds**
✅ **No errors**
❌ **Code file has old non-batched config** (will break on Beat restart)

**Result**: System working NOW but fragile. Code update ensures it keeps working.

---

## Deployment Steps

### On Production Server (10.30.25.46)

```bash
# 1. Pull latest code
cd /home/wardops/ward-flux-credobank
git pull origin main

# 2. Verify the fix
grep -A 3 '"ping-devices-icmp"' monitoring/celery_app.py
```

**Expected output:**
```python
"ping-devices-icmp": {
    "task": "monitoring.tasks.ping_all_devices_batched",  # ✅ BATCHED
    "schedule": 10.0,  # Every 10 seconds
},
```

### Restart Beat (Load New Schedule)

```bash
# 3. Stop Beat
docker-compose -f docker-compose.production-priority-queues.yml stop celery-beat

# 4. Remove Beat container
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-beat

# 5. Delete persistent schedule database (CRITICAL!)
docker-compose -f docker-compose.production-priority-queues.yml run --rm celery-beat sh -c "rm -f /app/celerybeat-schedule"

# 6. Start Beat with fresh schedule
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-beat

# 7. Wait 5 seconds for Beat to start
sleep 5
```

### Verify Deployment

```bash
# 8. Check Beat is using correct schedule
docker logs wardops-beat-prod 2>&1 | grep "ping-all-devices" | tail -3
```

**Expected output (10-second interval):**
```
Scheduler: Sending due task ping-all-devices (monitoring.tasks.ping_all_devices_batched)
```

```bash
# 9. Confirm batched execution continues
docker logs --since 30s wardops-worker-monitoring-prod 2>&1 | grep "Batch processed"
```

**Expected output:**
```
Batch processed 100 devices
Batch processed 100 devices
...
```

```bash
# 10. Check Beat health
docker ps | grep beat
```

**Should show**: `Up X minutes (healthy)` - NOT unhealthy

---

## What Changed

### Before (Code File - Wrong):
```python
"ping-devices-icmp": {
    "task": "monitoring.tasks.ping_all_devices",  # ❌ Non-batched
    "schedule": 30.0,  # Every 30 seconds
}
```

### After (Code File - Correct):
```python
"ping-devices-icmp": {
    "task": "monitoring.tasks.ping_all_devices_batched",  # ✅ Batched
    "schedule": 10.0,  # Every 10 seconds
}
```

### Beat Was Already Using (Cached):
```
monitoring.tasks.ping_all_devices_batched  # ✅ Batched (from old cache)
Every 10 seconds (from old cache)
```

---

## Expected Results After Deployment

### Detection Speed
| Metric | Before | After |
|--------|--------|-------|
| Ping interval | 30s (cached 10s) | 10s |
| Task type | Batched (cached) | Batched (in code) |
| Device detection | 0-10s (working) | 0-10s (guaranteed) |
| Alert latency | 10-20s (working) | 10-20s (guaranteed) |

### System Performance
| Metric | Value |
|--------|-------|
| Devices | 874 |
| Batches | 9 |
| Batch size | 100 devices |
| Processing time | 2-3 seconds total |
| Queue tasks | ~20/min (vs 1,752/min non-batched) |

---

## Why This Fix Is Critical

**Problem**: Beat was using a **cached schedule** from `celerybeat-schedule` file.

**Risk**: If Beat restarts for ANY reason (server reboot, container crash, deployment), it would load the **non-batched** schedule from code, causing:
- ❌ 876 individual tasks instead of 9 batches
- ❌ 5+ minute detection delays
- ❌ Queue backlog of 1,752 tasks/min
- ❌ Worker overload

**Solution**: Update code to match what Beat is doing, ensuring:
- ✅ Batched tasks persist across restarts
- ✅ 10-second detection guaranteed
- ✅ System resilience

---

## Verification Checklist

After deployment, confirm:

- [ ] Code shows `ping_all_devices_batched`
- [ ] Beat logs show 10-second interval
- [ ] Workers executing "Batch processed 100 devices"
- [ ] Beat container status: `healthy`
- [ ] No task errors in logs
- [ ] Device down detection: <10 seconds

---

## Rollback (If Needed)

If something goes wrong:

```bash
# Revert to previous commit
git reset --hard b4d3d18

# Restart Beat
docker-compose -f docker-compose.production-priority-queues.yml restart celery-beat
```

But **this should not be needed** - the batched tasks are ALREADY working!

---

## Summary

**What we're doing**: Updating code file to match the working Beat schedule
**Risk**: Very low - batched tasks already proven working
**Benefit**: Ensures 10-second detection persists across restarts
**Downtime**: None - Beat restart takes 5 seconds

**Status**: ✅ **READY TO DEPLOY**
