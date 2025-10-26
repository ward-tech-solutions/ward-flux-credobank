# Cache Clearing Diagnostic Logging Deployment

## Problem Statement

We deployed cache clearing code that SHOULD clear Redis cache when devices go DOWN or come UP. However:

✅ **Code IS deployed** - `clear_device_list_cache()` function exists in production
✅ **Devices ARE changing status** - We see "went DOWN" and "RECOVERED" messages
❌ **NO cache clearing messages** - We never see "Cleared X cache entries" messages

## Investigation So Far

1. **Verified code exists** in container:
   ```bash
   docker exec wardops-worker-monitoring-prod cat /app/monitoring/tasks_batch.py | grep -A 20 "def clear_device_list_cache"
   ```
   ✅ Function exists

2. **Verified logic exists**:
   - Line 118: `cache_clear_needed = False` initialized
   - Line 247: `cache_clear_needed = True` when status changes
   - Line 254: `if cache_clear_needed: clear_device_list_cache()`
   ✅ Logic exists

3. **Verified devices changing status**:
   ```
   [23:57:58] ✅ Device Chiatura-881 (10.195.49.5) RECOVERED
   [23:58:09] ✅ Device Chiatura-NVR (10.199.49.140) RECOVERED
   [23:58:58] ✅ Device PING-Chiatura-AP (10.195.49.252) RECOVERED
   ```
   ✅ Status changes happening

4. **Checked Redis**:
   - Only 1 cache key exists: `devices:list:*`
   - Redis client IS working (we see "Redis cache client initialized" message)

## Hypothesis

The cache clearing function has this logic:
```python
if keys:
    redis_client.delete(*keys)
    logger.info(f"Cleared {len(keys)} device list cache entries")
```

**If there are NO cache keys at that moment, the log message never appears!**

This could happen if:
1. The cache has already expired (30-second TTL)
2. The cache was never created in the first place
3. The function IS being called but there's nothing to clear

## Solution: Enhanced Diagnostic Logging

We've added comprehensive logging to track exactly what's happening:

### Changes Made (Commit: 75ae196)

1. **Enhanced `clear_device_list_cache()` function**:
   ```python
   if keys:
       redis_client.delete(*keys)
       logger.info(f"🗑️  Cleared {len(keys)} device list cache entries after status change")
   else:
       logger.info(f"🗑️  Cache clearing triggered but no cache keys found (cache was already empty)")
   ```
   - Now logs EVEN IF no keys exist

2. **Added pre-call logging**:
   ```python
   if cache_clear_needed:
       logger.info(f"🔔 Status change detected in batch - clearing device list cache")
       clear_device_list_cache()
   ```
   - Confirms the function is actually being called

3. **Changed exception logging from debug to warning**:
   ```python
   except Exception as e:
       logger.warning(f"⚠️  Cache clear error (non-critical): {e}")
   ```
   - Ensures errors are visible

## Deployment Instructions

### On Production Server (Flux - 10.30.25.46)

```bash
# Navigate to project directory
cd /home/wardops/ward-flux-credobank

# Pull latest code
git pull origin main

# Rebuild and restart monitoring worker
docker compose -f docker-compose.production-priority-queues.yml build celery-worker-monitoring
docker compose -f docker-compose.production-priority-queues.yml up -d celery-worker-monitoring

# Wait for worker to start
sleep 10

# Monitor for cache clearing messages
docker logs -f wardops-worker-monitoring-prod 2>&1 | grep --line-buffered -E "Status change detected|Cleared.*cache|cache was empty|went DOWN|RECOVERED"
```

Or use the deployment script:
```bash
bash deploy-diagnostic-logging.sh
```

## Expected Results After Deployment

When the next device goes DOWN or comes UP, you should see ONE of these message patterns:

### Scenario 1: Cache Exists and Gets Cleared
```
✅ Device Khashuri-881 (10.195.31.248) RECOVERED
🔔 Status change detected in batch - clearing device list cache
🗑️  Cleared 1 device list cache entries after status change
Batch processed 100 devices
```

### Scenario 2: Cache Was Already Empty
```
✅ Device Khashuri-881 (10.195.31.248) RECOVERED
🔔 Status change detected in batch - clearing device list cache
🗑️  Cache clearing triggered but no cache keys found (cache was already empty)
Batch processed 100 devices
```

### Scenario 3: Redis Client Issue
```
✅ Device Khashuri-881 (10.195.31.248) RECOVERED
🔔 Status change detected in batch - clearing device list cache
⚠️  Cache clearing triggered but Redis client is None
Batch processed 100 devices
```

### Scenario 4: Exception Occurred
```
✅ Device Khashuri-881 (10.195.31.248) RECOVERED
🔔 Status change detected in batch - clearing device list cache
⚠️  Cache clear error (non-critical): [exception message]
Batch processed 100 devices
```

### Scenario 5: Function Not Being Called (Bug!)
```
✅ Device Khashuri-881 (10.195.31.248) RECOVERED
Batch processed 100 devices
```
(No "Status change detected" message = `cache_clear_needed` flag is not being set)

## Next Steps

1. **Deploy** the diagnostic logging version
2. **Monitor** logs for the next device status change
3. **Identify** which scenario is occurring
4. **Fix** based on the scenario:
   - Scenario 1: ✅ Working correctly!
   - Scenario 2: Cache TTL might be too short, or API not being called
   - Scenario 3: Redis connection issue
   - Scenario 4: Specific bug to fix based on exception
   - Scenario 5: Logic bug in `cache_clear_needed` flag setting

## Files Changed

- `monitoring/tasks_batch.py` - Enhanced logging in cache clearing function
- `deploy-diagnostic-logging.sh` - Deployment script
- `CACHE-DIAGNOSTIC-DEPLOYMENT.md` - This file

## Git Commit

```
commit 75ae196
Add diagnostic logging for cache clearing investigation
```

## Timeline

- **Initial Issue**: Cache clearing code deployed but no log messages
- **Investigation**: Verified code exists, devices changing status, Redis working
- **Solution**: Added comprehensive diagnostic logging
- **Status**: Ready for deployment and testing
