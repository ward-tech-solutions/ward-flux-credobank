# CRITICAL: Memory Usage Issue - Redis + Worker Consuming 11.5GB

**Date:** 2025-10-23 12:35
**Status:** 🚨 CRITICAL - 74% RAM Usage (11.5GB / 15.6GB)
**Priority:** IMMEDIATE ACTION REQUIRED

---

## 🚨 Critical Memory Usage

**Total RAM:** 15.62 GB
**Used RAM:** ~14 GB (87.5%)
**Critical Containers:**

| Container | Memory | Percentage | Status |
|-----------|--------|------------|--------|
| **Redis** | **5.97 GB** | **38.2%** | 🚨 CRITICAL |
| **Celery Worker** | **5.58 GB** | **35.7%** | 🚨 CRITICAL |
| API | 1.60 GB | 10.2% | ⚠️ High |
| PostgreSQL | 275 MB | 1.7% | ✅ Normal |
| VictoriaMetrics | 70 MB | 0.4% | ✅ Normal |
| Beat | 81 MB | 0.5% | ✅ Normal |
| **TOTAL** | **~13.5 GB** | **~87%** | 🚨 **DANGER** |

---

## 🔍 Root Causes

### **Problem 1: Redis Cache Explosion (6GB)**

**Normal Redis Usage:** 100-500 MB
**Actual Usage:** 5.97 GB (12x over limit!)

**Cause:**
1. **Ping results caching without expiration**
   - 875 devices being pinged every 30 seconds
   - Cache keys created but not expiring properly
   - `ping_results` table has potentially millions of rows
   - Each cache entry ~1-5 KB × millions = GB of data

2. **Device list cache growing**
   - Device list API cache (30s TTL) might be accumulating
   - Filter combinations creating unique cache keys

3. **Redis persistence enabled**
   - `--appendonly yes` in docker-compose.yml
   - AOF (Append-Only File) keeps all operations in memory

**Evidence:**
```bash
docker stats:
wardops-redis-prod: 5.971GiB / 15.62GiB (38.23%)
```

---

### **Problem 2: Celery Worker Memory Leak (5.6GB)**

**Normal Worker Usage:** 500MB - 1.5GB
**Actual Usage:** 5.58 GB (4x over limit!)

**Causes:**

1. **SNMP DetachedInstanceError (Continuous)**
   ```python
   ERROR: DetachedInstanceError: Instance <MonitoringItem> is not bound to a Session
   ```
   - Happening every minute for `poll-all-devices-snmp`
   - Exception creates objects that aren't garbage collected
   - Worker processes never restart (no max-tasks-per-child)

2. **High Concurrency (50 workers)**
   ```yaml
   command: celery -A celery_app worker --loglevel=info --concurrency=50
   ```
   - 50 worker processes × ~100MB each = 5GB base memory
   - Plus active task memory
   - Too high for 875 devices

3. **No Task Limit (Workers Never Restart)**
   - Workers run indefinitely
   - Memory accumulates over time
   - No automatic cleanup

4. **Database Connections Per Worker**
   - 50 workers × potential DB connections = memory overhead
   - Connection pool: 100 base + 200 overflow = 300 max
   - Each connection ~5-10 MB

**Evidence:**
```bash
docker stats:
wardops-worker-prod: 5.582GiB / 15.62GiB (35.74%)

Database connections:
53 idle connections (from workers)
```

---

## 🚀 IMMEDIATE FIXES

### **Fix 1: Clear Redis Cache (Immediate Relief)**

**Impact:** Free up ~5GB RAM instantly

```bash
# Connect to Redis and flush cache
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB

# Verify memory usage
docker exec wardops-redis-prod redis-cli -a redispass INFO memory | grep used_memory_human
```

**Expected Result:** Redis memory drops from 6GB → ~50-100MB

---

### **Fix 2: Restart Celery Worker (Free 5.6GB)**

**Impact:** Free up accumulated memory

```bash
# Restart worker container
docker restart wardops-worker-prod

# Wait for startup
sleep 15

# Verify memory usage
docker stats --no-stream wardops-worker-prod
```

**Expected Result:** Worker memory drops from 5.6GB → ~1-2GB

---

### **Fix 3: Reduce Worker Concurrency**

**Current:** 50 workers (too high!)
**Recommended:** 20 workers

**Calculation:**
- 875 devices / 30 seconds = 29 tasks/second
- 20 workers can handle 40+ tasks/second
- Memory: 20 × 100MB = 2GB (vs 5GB current)

**File:** `docker-compose.production-local.yml` (line 92)

**Change:**
```yaml
# BEFORE (line 92):
command: celery -A celery_app worker --loglevel=info --concurrency=50

# AFTER:
command: celery -A celery_app worker --loglevel=info --concurrency=20 --max-tasks-per-child=1000
```

**What this does:**
- `--concurrency=20`: Reduce from 50 to 20 workers (save 3GB RAM)
- `--max-tasks-per-child=1000`: Restart worker after 1000 tasks (prevent memory leaks)

---

### **Fix 4: Fix SNMP DetachedInstanceError**

This is the **root cause** of worker memory leak.

**File:** `monitoring/tasks.py` (line ~75-130, SNMP task)

**Problem:** Same as datetime bug - accessing DB session after it's closed.

**Current Code (Broken):**
```python
@shared_task(name="monitoring.tasks.poll_device_snmp")
def poll_device_snmp(device_id: str, monitoring_item_id: str):
    db = SessionLocal()
    try:
        # Fetch monitoring item
        item = db.query(MonitoringItem).filter_by(id=monitoring_item_id).first()

        # Close DB session (to prevent idle transactions)
        db.close()

        # Try to access item.oid HERE (FAILS - session closed!)
        result = await snmp_poller.get(device_ip, item.oid, credentials)
        #                                          ^^^^^^^^
        # DetachedInstanceError: Instance not bound to Session!
```

**Fix:** Extract all needed data BEFORE closing session:
```python
@shared_task(name="monitoring.tasks.poll_device_snmp")
def poll_device_snmp(device_id: str, monitoring_item_id: str):
    db = SessionLocal()
    try:
        # Fetch monitoring item
        item = db.query(MonitoringItem).filter_by(id=monitoring_item_id).first()

        # EXTRACT DATA BEFORE CLOSING SESSION
        device_ip = device.ip
        item_oid = item.oid
        item_oid_name = item.oid_name
        # ... extract all needed fields

        # Now safe to close session
        db.commit()
        db.close()

        # Use extracted variables (not item.oid)
        result = await snmp_poller.get(device_ip, item_oid, credentials)
```

---

### **Fix 5: Add Redis Maxmemory Limit**

**File:** `docker-compose.production-local.yml` (line 28)

**Change:**
```yaml
# BEFORE (line 28):
command: redis-server --requirepass redispass --appendonly yes

# AFTER:
command: redis-server --requirepass redispass --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
```

**What this does:**
- `--maxmemory 1gb`: Limit Redis to 1GB max
- `--maxmemory-policy allkeys-lru`: Evict least recently used keys when full
- Prevents Redis from growing unbounded

---

### **Fix 6: Optimize Ping Results Caching**

**File:** `utils/cache.py`

**Problem:** Ping results might be cached indefinitely.

**Check Current TTL:**
```python
# In routers/devices.py (get_device_history endpoint)
redis_client.setex(cache_key, 30, json_lib.dumps(result))  # 30 seconds TTL ✅
```

**This should be OK** - 30 second TTL is good. But check if other endpoints are caching without TTL.

---

## 📋 Deployment Plan

### **Phase 1: Immediate Relief (Do NOW)**

```bash
cd /home/wardops/ward-flux-credobank

# Step 1: Flush Redis cache (free 5GB instantly)
echo "Flushing Redis cache..."
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB

# Step 2: Check Redis memory (should be ~50MB now)
echo "Redis memory after flush:"
docker exec wardops-redis-prod redis-cli -a redispass INFO memory | grep used_memory_human

# Step 3: Restart worker (free 5.6GB)
echo "Restarting worker..."
docker restart wardops-worker-prod

# Step 4: Wait for worker startup
sleep 20

# Step 5: Check memory usage
echo "Memory usage after fixes:"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

**Expected Result:**
- Redis: 5.97GB → ~50-100MB (saving 5.9GB)
- Worker: 5.58GB → ~1-2GB (saving 3.6GB)
- **Total saved: ~9.5GB**
- **New usage: ~4GB / 15.6GB (25%)** ✅

---

### **Phase 2: Permanent Fixes (Deploy Soon)**

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main

# Rebuild with new configuration
docker-compose -f docker-compose.production-local.yml build --no-cache celery-worker redis

# Restart with new settings
docker-compose -f docker-compose.production-local.yml up -d redis celery-worker celery-beat

# Monitor memory
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"'
```

---

## ✅ Verification

### **1. Check Redis Memory (Should be < 500MB)**

```bash
docker exec wardops-redis-prod redis-cli -a redispass INFO memory | grep -E "(used_memory_human|maxmemory)"
```

**Expected:**
```
used_memory_human:150.00M
maxmemory_human:1.00G
```

### **2. Check Worker Memory (Should be < 2GB)**

```bash
docker stats --no-stream wardops-worker-prod
```

**Expected:**
```
wardops-worker-prod: 1.5GiB / 15.62GiB (9.6%)
```

### **3. Check Worker Configuration**

```bash
docker exec wardops-worker-prod celery -A celery_app inspect stats | grep -E "(pool|max-tasks-per-child)"
```

**Expected:**
```
"pool": {"max-concurrency": 20}
"max-tasks-per-child": 1000
```

### **4. Monitor for SNMP Errors (Should decrease after fix)**

```bash
docker logs wardops-worker-prod --tail 100 --follow | grep -i "DetachedInstanceError"
```

**Expected:** No more DetachedInstanceError messages (after SNMP fix deployed)

---

## 📊 Expected Results

### **Before Fixes:**
- Redis: 5.97 GB (38.2%)
- Worker: 5.58 GB (35.7%)
- Total: 11.55 GB (74%)
- **Server at 87% RAM usage** 🚨

### **After Immediate Fixes:**
- Redis: ~100 MB (0.6%)
- Worker: ~1.5 GB (9.6%)
- Total: ~3 GB (19%)
- **Server at 30-40% RAM usage** ✅

### **After Permanent Fixes:**
- Redis: < 500 MB (capped at 1GB)
- Worker: ~1-2 GB (20 workers, auto-restart)
- Total: ~3-4 GB (20-25%)
- **Server at 35-45% RAM usage** ✅
- **No more memory leaks** ✅

---

## 🎯 Files to Change

1. **docker-compose.production-local.yml**
   - Line 28: Add Redis maxmemory limit
   - Line 92: Reduce worker concurrency + add max-tasks-per-child

2. **monitoring/tasks.py**
   - Lines 75-130: Fix SNMP DetachedInstanceError
   - Extract all DB fields before closing session

---

## 📝 Related Issues

- ✅ Real-time monitoring broken (FIXED - datetime bug)
- ✅ Ping tasks failing (FIXED - datetime bug)
- 🚨 Memory usage 87% (THIS ISSUE)
- ⚠️ SNMP polling broken (DetachedInstanceError - causes memory leak)
- ⚠️ Worker memory growing (No max-tasks-per-child)
- ⚠️ Redis unbounded growth (No maxmemory limit)

---

**Priority:** 🚨 **EXECUTE PHASE 1 IMMEDIATELY**

Server at 87% RAM usage is **dangerous** - could crash or start swapping anytime.

**Run Phase 1 commands NOW, then we'll prepare Phase 2 fixes.**

---

**Created:** 2025-10-23 12:40
**Status:** Awaiting immediate action (Phase 1)
**Urgency:** CRITICAL - Execute within minutes!
