# Immediate Memory Fix - Manual Commands

**Status:** 🚨 CRITICAL - Redis 6GB + Worker 5.6GB = 87% RAM usage

---

## 🚀 Quick Manual Fix (If Script Doesn't Work)

### **Step 1: Check Redis Auth**

```bash
# Try without password
docker exec wardops-redis-prod redis-cli PING
```

**If it returns `PONG`:** Redis has no auth (use commands without `-a`)
**If it returns error:** Redis requires password (use commands with `-a redispass`)

---

### **Step 2: Flush Redis Cache (Free 6GB)**

**Without password:**
```bash
docker exec wardops-redis-prod redis-cli FLUSHDB
```

**With password (if needed):**
```bash
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB
```

---

### **Step 3: Verify Redis Memory**

**Without password:**
```bash
docker exec wardops-redis-prod redis-cli INFO memory | grep used_memory_human
```

**With password (if needed):**
```bash
docker exec wardops-redis-prod redis-cli -a redispass INFO memory | grep used_memory_human
```

**Expected:** `used_memory_human:50.00M` (was 6GB)

---

### **Step 4: Restart Worker (Free 5.6GB)**

```bash
docker restart wardops-worker-prod
```

Wait 20 seconds for startup:
```bash
sleep 20
```

---

### **Step 5: Verify Memory Usage**

```bash
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

**Expected:**
```
NAME                           MEM USAGE / LIMIT     MEM %
wardops-redis-prod             ~100MB / 15.62GiB     ~0.6%  ✅
wardops-worker-prod            ~1.5GB / 15.62GiB     ~9.6%  ✅
Total RAM usage: ~30% (was 87%)
```

---

## ✅ Success Criteria

- ✅ Redis memory: < 200 MB (was 6GB)
- ✅ Worker memory: 1-2 GB (was 5.6GB)
- ✅ Total RAM usage: 30-40% (was 87%)
- ✅ System responsive and stable

---

## 📋 After Immediate Fix

Deploy permanent fixes:

```bash
cd /home/wardops/ward-flux-credobank
git pull origin main

# Rebuild with new config (Redis maxmemory + worker concurrency)
docker-compose -f docker-compose.production-local.yml build --no-cache redis celery-worker

# Deploy
docker-compose -f docker-compose.production-local.yml up -d redis celery-worker celery-beat
```

---

## 🔍 Monitor Next 10 Minutes

**Watch memory in real-time:**
```bash
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"'
```

**Check Redis memory growth:**
```bash
docker exec wardops-redis-prod redis-cli INFO memory | grep used_memory_human
```

**Expected behavior:**
- Redis will slowly grow as cache rebuilds (50MB → 300MB over 10 min)
- Worker stays stable at 1-2GB
- Total RAM stays under 40%

---

## ⚠️ What Was The Problem?

**Redis (6GB):**
- Cache growing unbounded
- No maxmemory limit configured
- 875 devices × 30s pings × millions of cache entries = 6GB

**Worker (5.6GB):**
- 50 workers running (too many)
- SNMP DetachedInstanceError leaking memory
- No auto-restart (max-tasks-per-child)
- Memory accumulating over hours/days

**Permanent fixes:**
- Redis: Capped at 1GB with LRU eviction
- Worker: Reduced to 20 workers with auto-restart after 1000 tasks

---

**Execute these commands NOW - your server is at critical memory levels!**
