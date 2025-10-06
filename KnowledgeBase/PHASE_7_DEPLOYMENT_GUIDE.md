# Phase 7: Polling Engine Deployment - COMPLETE ✓

**Implementation Date**: October 6, 2025
**Status**: Ready for Deployment
**Infrastructure**: Docker-based deployment ready

---

## Overview

Phase 7 provides the complete infrastructure for live SNMP polling and metric collection. The system uses:
- **VictoriaMetrics** for time-series metric storage
- **Redis** for distributed task queue
- **Celery** for background SNMP polling
- **Celery Beat** for scheduled polling intervals

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WARD FLUX CORE API                       │
│                   (FastAPI on port 5001)                    │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──► Creates Monitoring Items (via templates)
                │
┌───────────────▼─────────────────────────────────────────────┐
│                    CELERY BEAT (Scheduler)                  │
│           Triggers polling every 60 seconds                 │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──► Queues tasks in Redis
                │
┌───────────────▼─────────────────────────────────────────────┐
│                    REDIS (Task Queue)                       │
│                  localhost:6379                             │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──► Tasks consumed by workers
                │
┌───────────────▼─────────────────────────────────────────────┐
│                  CELERY WORKERS                             │
│            (1-N workers for parallel polling)               │
│                                                             │
│  ┌─────────────────────────────────────────────┐          │
│  │  poll_device_item(item_id)                  │          │
│  │  1. Get device & credentials from DB        │          │
│  │  2. Poll SNMP OID                           │          │
│  │  3. Store metric in VictoriaMetrics         │          │
│  │  4. Update last_poll timestamp              │          │
│  └─────────────────────────────────────────────┘          │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──► Writes metrics
                │
┌───────────────▼─────────────────────────────────────────────┐
│               VICTORIAMETRICS                               │
│         Time-Series Database (localhost:8428)               │
│         - 12 month retention                                │
│         - Optimized for high cardinality                    │
│         - PromQL query language                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. VictoriaMetrics
**Purpose**: Time-series database for storing SNMP metrics
**Port**: 8428
**Features**:
- High-performance metric storage
- 12-month retention policy
- Prometheus-compatible API
- Grafana integration ready

**Metrics Format**:
```
snmp_cpu_5sec{device="Core-Router-01",vendor="Cisco",ip="192.168.1.1"} 25.5
snmp_mem_free{device="Core-Router-01",vendor="Cisco",ip="192.168.1.1"} 512000000
```

---

### 2. Redis
**Purpose**: Message broker and result backend for Celery
**Port**: 6379
**Features**:
- Persistent task queue
- Result storage
- Fast in-memory operations

---

### 3. Celery Worker
**Purpose**: Background task execution
**Tasks**:
- `poll_device_item` - Poll single monitoring item
- `poll_all_devices` - Poll all enabled items (runs every 60s)
- `check_device_health` - ICMP health checks (every 5min)
- `cleanup_old_data` - Data maintenance (hourly)
- `poll_device_bulk` - Poll all items for one device

**Configuration**:
```python
# celery_app.py
task_time_limit = 300  # 5 minutes
task_soft_time_limit = 240  # 4 minutes
worker_prefetch_multiplier = 4
worker_max_tasks_per_child = 1000
```

---

### 4. Celery Beat
**Purpose**: Periodic task scheduler
**Schedule**:
```python
{
    'poll-all-devices': {
        'task': 'monitoring.tasks.poll_all_devices',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-old-data': {
        'task': 'monitoring.tasks.cleanup_old_data',
        'schedule': crontab(minute=0),  # Every hour
    },
    'check-device-health': {
        'task': 'monitoring.tasks.check_device_health',
        'schedule': 300.0,  # Every 5 minutes
    },
}
```

---

## Deployment Instructions

### Prerequisites
```bash
# Install Docker (if not already installed)
# macOS:
brew install --cask docker

# Or download from https://www.docker.com/products/docker-desktop

# Install Python dependencies
pip3 install celery redis
```

### Option 1: Automated Deployment (Docker)

```bash
# 1. Start monitoring stack
./start_monitoring.sh

# Output:
# ✓ Docker found
# ✓ VictoriaMetrics running on http://localhost:8428
# ✓ Redis running on localhost:6379
# ✓ Celery worker started
# ✓ Celery beat started
```

### Option 2: Manual Deployment

```bash
# 1. Start Docker services
docker-compose -f docker-compose.monitoring.yml up -d

# 2. Verify services
docker ps
# Should show: ward-victoriametrics, ward-redis, ward-grafana

# 3. Start Celery worker
celery -A celery_app worker --loglevel=info

# 4. Start Celery beat (in separate terminal)
celery -A celery_app beat --loglevel=info
```

### Option 3: Local Installation (without Docker)

```bash
# Install VictoriaMetrics
curl -L https://github.com/VictoriaMetrics/VictoriaMetrics/releases/download/v1.93.0/victoria-metrics-darwin-amd64-v1.93.0.tar.gz | tar xz
./victoria-metrics-prod --retentionPeriod=12

# Install Redis
brew install redis  # macOS
redis-server

# Start Celery
celery -A celery_app worker --loglevel=info &
celery -A celery_app beat --loglevel=info &
```

---

## Verification

### 1. Check Docker Containers
```bash
docker ps | grep ward

# Expected output:
# ward-victoriametrics
# ward-redis
# ward-grafana
```

### 2. Check VictoriaMetrics
```bash
curl http://localhost:8428/api/v1/status/tsdb

# Should return JSON with database stats
```

### 3. Check Redis
```bash
redis-cli ping
# Expected: PONG
```

### 4. Check Celery Workers
```bash
celery -A celery_app inspect active

# Should show active workers
```

### 5. Monitor Celery Logs
```bash
tail -f logs/celery_worker.log

# Should show polling activity:
# [INFO] Polled Core-Router-01 - cpu_5sec: 25.5
# [INFO] Polled Core-Router-01 - mem_free: 512000000
```

---

## End-to-End Test

### Complete Workflow Test

```bash
# 1. Ensure monitoring stack is running
docker ps | grep ward

# 2. Add test device (via API or database)
# Already have devices from Phase 4

# 3. Attach SNMP credentials (Phase 6)
# Already have credentials attached

# 4. Auto-detect vendor and assign template (Phase 6)
# Already have templates assigned

# 5. Verify monitoring items exist
sqlite3 database.db "SELECT COUNT(*) FROM monitoring_items WHERE enabled=1;"

# 6. Trigger manual poll
python3 -c "
from monitoring.tasks import poll_all_devices
result = poll_all_devices.delay()
print(f'Task ID: {result.id}')
"

# 7. Check task result
python3 -c "
from celery_app import app
from celery.result import AsyncResult
result = AsyncResult('task-id-from-step-6', app=app)
print(f'Status: {result.status}')
print(f'Result: {result.result}')
"

# 8. Query VictoriaMetrics for stored metrics
curl 'http://localhost:8428/api/v1/query?query=snmp_cpu_5sec' | python3 -m json.tool

# Expected: Time-series data for CPU metrics
```

---

## Monitoring & Observability

### Celery Flower (Web UI)
```bash
# Install Flower
pip3 install flower

# Start Flower
celery -A celery_app flower --port=5555

# Access: http://localhost:5555
```

**Flower Features**:
- Real-time task monitoring
- Worker status
- Task history
- Task retry/revoke
- Performance graphs

### Grafana Dashboards

Access Grafana: http://localhost:3000
- **Username**: admin
- **Password**: admin

**Add VictoriaMetrics Data Source**:
1. Configuration → Data Sources → Add Prometheus
2. URL: `http://victoriametrics:8428`
3. Save & Test

**Import Dashboard**:
1. Create → Import
2. Use dashboard ID: 10229 (VictoriaMetrics dashboard)

---

## Scaling

### Horizontal Scaling

**Run Multiple Workers**:
```bash
# Worker 1 (general tasks)
celery -A celery_app worker --loglevel=info -n worker1@%h

# Worker 2 (high-priority)
celery -A celery_app worker --loglevel=info -n worker2@%h --queues=high_priority

# Worker 3 (bulk polling)
celery -A celery_app worker --loglevel=info -n worker3@%h --queues=bulk_polling
```

**Concurrency Tuning**:
```bash
# More concurrent tasks per worker
celery -A celery_app worker --concurrency=8 --loglevel=info

# Use gevent for I/O-bound tasks (SNMP)
celery -A celery_app worker --pool=gevent --concurrency=100
```

### Vertical Scaling

**Increase VictoriaMetrics Resources**:
```yaml
# docker-compose.monitoring.yml
victoriametrics:
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 2G
```

---

## Troubleshooting

### Issue: Celery can't connect to Redis
```bash
# Check Redis is running
redis-cli ping

# Check Redis URL in .env
echo $REDIS_URL
# Should be: redis://localhost:6379/0

# Test connection
python3 -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"
```

### Issue: VictoriaMetrics not storing metrics
```bash
# Check VictoriaMetrics logs
docker logs ward-victoriametrics

# Test write endpoint
curl -X POST http://localhost:8428/api/v1/import/prometheus \
  -d 'test_metric{label="value"} 123'

# Verify write
curl 'http://localhost:8428/api/v1/query?query=test_metric'
```

### Issue: Tasks not running
```bash
# Check Celery beat is running
ps aux | grep "celery.*beat"

# Check beat schedule
cat logs/celerybeat-schedule.db

# Manually trigger task
python3 -c "from monitoring.tasks import poll_all_devices; poll_all_devices.delay()"

# Check worker logs
tail -f logs/celery_worker.log
```

---

## Performance Metrics

### Expected Performance

| Metric | Value |
|--------|-------|
| Items per minute | 1000+ |
| SNMP query latency | 50-200ms |
| Metric write latency | <10ms |
| Task queue latency | <100ms |
| Worker CPU usage | 10-30% |
| VictoriaMetrics RAM | 500MB-2GB |
| Redis RAM | 100-500MB |

### Optimization Tips

1. **Batch SNMP Queries**: Use SNMP BULK GET for multiple OIDs
2. **Adjust Polling Intervals**: Critical items=60s, Standard=300s
3. **Worker Concurrency**: Start with 4, increase based on load
4. **Use Gevent Pool**: Better for I/O-bound SNMP queries
5. **VictoriaMetrics Caching**: Queries are cached automatically

---

## Files Created

1. `docker-compose.monitoring.yml` - Docker services config
2. `celery_app.py` - Celery application and schedule
3. `monitoring/tasks.py` - Celery task definitions (already existed, enhanced)
4. `start_monitoring.sh` - Automated startup script
5. `stop_monitoring.sh` - Shutdown script

---

## Summary

Phase 7 delivers:
- ✅ Complete polling infrastructure
- ✅ Docker-based deployment
- ✅ Automated startup/shutdown scripts
- ✅ Celery task definitions
- ✅ VictoriaMetrics integration
- ✅ Redis task queue
- ✅ Scheduled polling (every 60s)
- ✅ Health checks (every 5min)
- ✅ Horizontal scaling support
- ✅ Monitoring & observability (Flower, Grafana)

**Overall Progress**: 70% complete (7 of 10 phases)

**Ready for**: Live SNMP polling with real network devices

**Next**: Phase 8 - Auto-Discovery (optional) or Phase 9 - UI Development
