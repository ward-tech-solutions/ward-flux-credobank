# Permanent Fix: Task Priority Queues

**Problem:** 65,941 tasks backed up in queue, `evaluate_alert_rules` delayed by 3+ hours

**Root Cause:** All tasks go to same queue with same priority
- `ping_device` scheduled every 30s for 875 devices = ~1,750 tasks/minute
- `poll_device_snmp` scheduled every 60s for 875 devices = ~875 tasks/minute
- `evaluate_alert_rules` scheduled every 60s = 1 task/minute
- **Total:** ~2,626 tasks/minute queued
- **Worker capacity:** ~120-180 tasks/minute (20 workers × 6-9 tasks/min)
- **Queue grows by:** ~2,400 tasks/minute!

**Solution:** Use Celery task routing with priority queues

---

## Option 1: Separate Queues (RECOMMENDED)

Create 3 queues with dedicated workers:
1. **High priority queue:** `evaluate_alert_rules` only
2. **Medium priority queue:** `ping_device` (critical for monitoring)
3. **Low priority queue:** `poll_device_snmp` (metrics only)

### Implementation

**1. Update celery_app.py:**

```python
# Task routing - send tasks to different queues
app.conf.task_routes = {
    # CRITICAL: Alert evaluation (high priority)
    'monitoring.tasks.evaluate_alert_rules': {'queue': 'alerts', 'priority': 10},
    'monitoring.tasks.check_device_health': {'queue': 'alerts', 'priority': 10},

    # IMPORTANT: Ping monitoring (medium priority)
    'monitoring.tasks.ping_all_devices': {'queue': 'monitoring', 'priority': 5},
    'monitoring.tasks.ping_device': {'queue': 'monitoring', 'priority': 5},

    # NORMAL: SNMP polling (low priority, can be delayed)
    'monitoring.tasks.poll_all_devices_snmp': {'queue': 'snmp', 'priority': 1},
    'monitoring.tasks.poll_device_snmp': {'queue': 'snmp', 'priority': 1},

    # MAINTENANCE: Cleanup tasks
    'monitoring.tasks.cleanup_old_ping_results': {'queue': 'maintenance', 'priority': 0},
}
```

**2. Update docker-compose.production-local.yml:**

```yaml
  # High priority worker - alerts only (small, fast)
  celery-worker-alerts:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: wardops-worker-alerts-prod
    command: celery -A celery_app worker --loglevel=info --concurrency=4 -Q alerts
    environment:
      DATABASE_URL: postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
      REDIS_URL: redis://:redispass@redis:6379/0
      VICTORIA_URL: http://victoriametrics:8428
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Medium priority worker - ping monitoring (most workers)
  celery-worker-monitoring:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: wardops-worker-monitoring-prod
    command: celery -A celery_app worker --loglevel=info --concurrency=20 -Q monitoring
    environment:
      DATABASE_URL: postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
      REDIS_URL: redis://:redispass@redis:6379/0
      VICTORIA_URL: http://victoriametrics:8428
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Low priority worker - SNMP polling (can be slow)
  celery-worker-snmp:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: wardops-worker-snmp-prod
    command: celery -A celery_app worker --loglevel=info --concurrency=15 -Q snmp
    environment:
      DATABASE_URL: postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops
      REDIS_URL: redis://:redispass@redis:6379/0
      VICTORIA_URL: http://victoriametrics:8428
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
```

**Benefits:**
- ✅ Alert evaluation always runs within 1 minute
- ✅ Pings processed quickly (30s interval maintained)
- ✅ SNMP can queue up without affecting alerts
- ✅ Easy to scale each queue independently

---

## Option 2: Increase Worker Concurrency (QUICK FIX)

**Current:** 20 workers = ~120-180 tasks/minute
**Needed:** ~2,626 tasks/minute
**Required:** ~150-200 workers

**Update docker-compose.production-local.yml:**

```yaml
  celery-worker:
    command: celery -A celery_app worker --loglevel=info --concurrency=100 --max-tasks-per-child=1000
```

**Warning:** This will use more CPU and memory, but ensures all tasks process.

**Benefits:**
- ✅ Simple one-line change
- ✅ No code changes needed
- ⚠️ High resource usage

---

## Option 3: Reduce Task Volume (OPTIMIZATION)

**Current bottleneck:** Too many individual tasks

**Batch processing:**
- Instead of 875 individual `ping_device` tasks, create 10 batch tasks (87 devices each)
- Instead of 875 individual `poll_device_snmp` tasks, process in batches

**Implementation:**
- Modify `ping_all_devices` to ping in batches of 50-100 devices per task
- Modify `poll_all_devices_snmp` to poll in batches

**Benefits:**
- ✅ Reduces queue size by 10-20x
- ✅ Lower Redis memory usage
- ✅ Fewer context switches
- ⚠️ Requires code changes

---

## Recommended Immediate Action

**Deploy Option 2 NOW (increase concurrency to 100):**

```bash
# Edit docker-compose.production-local.yml
sed -i 's/--concurrency=20/--concurrency=100/' docker-compose.production-local.yml

# Restart worker
docker-compose -f docker-compose.production-local.yml up -d celery-worker
```

**Then implement Option 1 (priority queues) for long-term solution.**

---

## Monitoring After Fix

**Check queue size stays manageable:**
```bash
watch -n 5 'docker-compose -f docker-compose.production-local.yml exec redis redis-cli -a redispass LLEN celery'
```

**Expected:** Queue size < 1000 tasks at all times

**Check alert evaluation runs regularly:**
```bash
docker-compose -f docker-compose.production-local.yml logs -f celery-worker | grep "Starting alert rule evaluation"
```

**Expected:** Message every 60 seconds

**Check alerts are created:**
```bash
docker-compose -f docker-compose.production-local.yml exec postgres psql -U ward_admin -d ward_ops -c \
  "SELECT COUNT(*), MAX(triggered_at), NOW() - MAX(triggered_at) as age
   FROM alert_history
   WHERE triggered_at > NOW() - INTERVAL '10 minutes';"
```

**Expected:** Recent alerts within last few minutes

---

**Created:** 2025-10-23 (EMERGENCY)
**Priority:** 🔥 CRITICAL - Alerts delayed by hours
**Status:** Ready to deploy
