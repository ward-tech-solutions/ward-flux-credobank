# WARD-OPS OPTIMIZATION OPPORTUNITIES
## Post-VictoriaMetrics Migration Analysis

**Date**: October 24, 2025
**Current State**: Phases 1-3 Complete (Storage at 6%)
**Status**: Production Ready - Identifying Next Optimizations

---

## COMPLETED OPTIMIZATIONS ✅

### Phase 1-3: VictoriaMetrics Migration
- **✅ Dual Write**: Writing to both PostgreSQL + VictoriaMetrics
- **✅ Read Migration**: API endpoints reading from VictoriaMetrics
- **✅ WebSocket Fix**: Eliminated 46-second transaction locks
- **✅ Parallel Queries**: Device history queries 2x faster
- **✅ Batch Queries**: 50 IPs per query to avoid HTTP 422
- **✅ Storage Cleanup**: Disk usage reduced from 43% → 6%

### Performance Gains Achieved
| Metric | Before | After | Improvement |
|--------|---------|--------|-------------|
| Dashboard load | 60+ seconds | 30-80ms | **750x faster** |
| Device list | 60+ seconds | 200ms | **300x faster** |
| Device history | 30s timeout | 1.5-4.5s | **20x faster** |
| WebSocket poll | 46s lock | 360ms | **128x faster** |
| Storage growth | Uncontrolled | Managed | Capped at 6% |

---

## OPTIMIZATION CATEGORIES

### 🔥 **TIER 1: Critical Performance Wins** (Days to weeks)
High impact, low effort optimizations that will provide immediate user experience improvements.

### 🚀 **TIER 2: Architectural Improvements** (Weeks to months)
Medium-to-high impact changes requiring more planning and testing.

### 🛠️ **TIER 3: Future Enhancements** (Months to quarters)
Long-term improvements for scalability and advanced features.

---

## 🔥 TIER 1: CRITICAL PERFORMANCE WINS

### 1. **Complete Phase 4 - Stop PostgreSQL Writes**

**Current Problem:**
- Still writing to `ping_results` table (line 135 in tasks_batch.py)
- Database continues to grow unnecessarily
- Wasting disk I/O and storage

**Solution:**
```python
# monitoring/tasks_batch.py - Remove line 135
# db.add(ping_result)  # REMOVE THIS - We use VictoriaMetrics now!
```

**Expected Impact:**
- Stop PostgreSQL growth completely
- Free up database I/O for other queries
- Reduce monitoring worker memory usage
- **Effort**: 5 minutes
- **Risk**: Very Low (VM already has all data)

**Implementation:**
```bash
# 1. Comment out PostgreSQL write
# 2. Restart monitoring workers
docker-compose -f docker-compose.production-priority-queues.yml restart wardops-worker-monitoring-prod

# 3. Monitor for 1 hour, verify no issues
# 4. If stable, archive old ping_results data
```

---

### 2. **Fix Redis Authentication**

**Current Problem:**
- Cache returning `NOAUTH Authentication required` errors
- Every request hits VictoriaMetrics (no caching)
- Some requests taking 4.5+ seconds on cache misses

**Root Cause:**
Redis requires password but API not configured with credentials.

**Solution:**
```yaml
# docker-compose.production-priority-queues.yml
environment:
  REDIS_PASSWORD: ${REDIS_PASSWORD}  # Add this
  REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
```

```python
# utils/cache.py or wherever redis_client is initialized
redis_client = redis.Redis(
    host='redis',
    port=6379,
    password=os.getenv('REDIS_PASSWORD'),  # Add this
    decode_responses=True
)
```

**Expected Impact:**
- 90% cache hit rate on repeated requests
- Device history: 4.5s → 50ms on cache hits
- Dashboard stats: 200ms → 10ms on cache hits
- **Effort**: 15 minutes
- **Risk**: Low

---

### 3. **Auto-Refresh Request Debouncing**

**Current Problem:**
User reported: "When monitor page timer is below 15s and I open any device information - it gets slower"

**Root Cause:**
- Multiple concurrent requests during auto-refresh
- Frontend doesn't check if previous request is pending
- No request deduplication

**Solution (Frontend):**
```javascript
// frontend/src/pages/MonitorPage.jsx
let refreshInProgress = false;
let lastRefreshTime = 0;

async function refreshDevices() {
    // Don't start new refresh if one is running
    if (refreshInProgress) {
        console.log('Refresh already in progress, skipping');
        return;
    }

    // Rate limiting: don't refresh faster than every 5 seconds
    const now = Date.now();
    if (now - lastRefreshTime < 5000) {
        console.log('Refresh too soon, skipping');
        return;
    }

    refreshInProgress = true;
    lastRefreshTime = now;

    try {
        await fetchDeviceList();
    } finally {
        refreshInProgress = false;
    }
}

// Disable auto-refresh when modal is open
function openDeviceModal(deviceId) {
    pauseAutoRefresh();  // New function
    // ... open modal
}

function closeDeviceModal() {
    resumeAutoRefresh();  // New function
    // ... close modal
}
```

**Solution (Backend - Optional):**
```python
# Add request coalescing middleware
from contextlib import asynccontextmanager
import asyncio

# In-flight request tracker
_inflight_requests = {}

@asynccontextmanager
async def coalesce_request(cache_key: str):
    """If same request is in flight, wait for it instead of duplicating work"""
    if cache_key in _inflight_requests:
        # Another request is already processing this
        logger.debug(f"Coalescing request: {cache_key}")
        await _inflight_requests[cache_key]
        return

    # Create future for this request
    future = asyncio.Future()
    _inflight_requests[cache_key] = future

    try:
        yield
    finally:
        future.set_result(True)
        del _inflight_requests[cache_key]
```

**Expected Impact:**
- Eliminate request contention during auto-refresh
- Faster response when modal is open
- Reduced VictoriaMetrics load during high-frequency polling
- **Effort**: 1-2 hours
- **Risk**: Low

---

### 4. **Archive Old PostgreSQL Ping Data**

**Current State:**
- ping_results table: 5.4M rows, 1.3GB
- All data now in VictoriaMetrics
- Old PostgreSQL data no longer needed

**Solution:**
```sql
-- Keep only last 7 days for emergency fallback
DELETE FROM ping_results
WHERE timestamp < NOW() - INTERVAL '7 days';

-- Reclaim space
VACUUM FULL ANALYZE ping_results;

-- Or just truncate entirely if confident
-- TRUNCATE TABLE ping_results;
```

**Expected Impact:**
- Free 1.2GB disk space (1.3GB → ~50MB)
- Faster database backups
- Reduced WAL log size
- **Effort**: 5 minutes (but runs for 10-30 minutes)
- **Risk**: Low (data in VictoriaMetrics)

**Safety Check:**
```bash
# Verify VictoriaMetrics has data for last 7 days
curl -s "http://victoriametrics:8428/api/v1/query?query=count(device_ping_status)" | jq

# Count should be 875 (all devices)
```

---

### 5. **VictoriaMetrics Query Result Caching**

**Current Problem:**
- Every API request hits VictoriaMetrics
- Same query executed multiple times within seconds
- Redis auth broken (see optimization #2)

**Solution - In-Memory Cache Layer:**
```python
# utils/victoriametrics_client.py
from functools import lru_cache
import hashlib
import time

class VictoriaMetricsClient:
    def __init__(self):
        self._query_cache = {}  # {query_hash: (result, expire_time)}
        self._cache_ttl = 10  # 10 seconds

    def query_with_cache(self, query: str, ttl: int = 10) -> Dict[str, Any]:
        """Query with in-memory caching"""
        # Create cache key
        query_hash = hashlib.md5(query.encode()).hexdigest()

        # Check cache
        now = time.time()
        if query_hash in self._query_cache:
            result, expire_time = self._query_cache[query_hash]
            if now < expire_time:
                logger.debug(f"Cache hit for query: {query[:50]}")
                return result

        # Cache miss - query VM
        result = self.query(query)

        # Store in cache
        self._query_cache[query_hash] = (result, now + ttl)

        # Cleanup old entries (simple LRU)
        if len(self._query_cache) > 1000:
            # Remove expired entries
            self._query_cache = {
                k: v for k, v in self._query_cache.items()
                if v[1] > now
            }

        return result
```

**Expected Impact:**
- 80% reduction in VictoriaMetrics queries during traffic spikes
- Dashboard stats: 200ms → 20ms on cache hits
- Works even if Redis is down
- **Effort**: 1 hour
- **Risk**: Very Low

---

### 6. **Optimize Device History Query Resolution**

**Current State:**
```python
# Querying at 5-minute resolution for all time ranges
vm_client.get_device_status_history(device_id, hours, "5m")
```

**Problem:**
- 24h at 5m = 288 data points ✅ Good
- 7d at 5m = 2,016 points ⚠️ Too many
- 30d at 5m = 8,640 points ❌ Excessive

**Solution - Dynamic Resolution:**
```python
def get_optimal_step(hours: int) -> str:
    """Choose query resolution based on time range"""
    if hours <= 24:
        return "5m"   # 288 points
    elif hours <= 168:  # 7 days
        return "15m"  # 672 points
    else:  # 30 days
        return "1h"   # 720 points
```

```python
# routers/devices.py
time_map = {"24h": 24, "7d": 168, "30d": 720}
hours = time_map.get(time_range, 24)
step = get_optimal_step(hours)  # Dynamic!

status_future = executor.submit(
    vm_client.get_device_status_history,
    str(device.id),
    hours,
    step  # Use dynamic resolution
)
```

**Expected Impact:**
- 30d queries: 8,640 points → 720 points (12x less data)
- Faster chart rendering on frontend
- Reduced network bandwidth
- VictoriaMetrics queries 5-10x faster
- **Effort**: 15 minutes
- **Risk**: None (just visualization smoothing)

---

### 7. **Add VictoriaMetrics Connection Pooling**

**Current Problem:**
```python
# Creating new HTTP connection for every query
response = requests.get(self.query_url, params=params, timeout=30)
```

**Solution:**
```python
# utils/victoriametrics_client.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class VictoriaMetricsClient:
    def __init__(self, base_url: str = "http://victoriametrics:8428"):
        self.base_url = base_url.rstrip("/")

        # Create session with connection pooling
        self.session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(
            pool_connections=20,    # Keep 20 connections open
            pool_maxsize=50,        # Max 50 connections total
            max_retries=retry_strategy
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def query(self, query: str) -> Dict[str, Any]:
        """Use session instead of requests.get"""
        response = self.session.get(
            self.query_url,
            params={"query": query},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
```

**Expected Impact:**
- Eliminate TCP connection overhead (30-50ms per request)
- Parallel queries 2-3x faster
- Automatic retries on transient failures
- **Effort**: 20 minutes
- **Risk**: Very Low

---

## 🚀 TIER 2: ARCHITECTURAL IMPROVEMENTS

### 8. **WebSocket Delta Updates (Instead of Full Device List)**

**Current Problem:**
```python
# Sending full device list (875 devices × ~500 bytes = 437KB) every poll
devices = session.query(StandaloneDevice).all()
# ... send all devices to frontend
```

**Solution:**
```python
# Only send devices that changed since last poll
from datetime import datetime, timedelta

class WebSocketManager:
    def __init__(self):
        self._last_states = {}  # {device_id: {"status": "up", "updated": timestamp}}

    async def send_device_updates(self, websocket):
        """Send only changed devices"""
        devices = session.query(StandaloneDevice).all()
        device_ips = [d.ip for d in devices if d.ip]
        ping_lookup = vm_client.get_latest_ping_for_devices(device_ips)

        changes = []
        now = datetime.utcnow()

        for device in devices:
            ping = ping_lookup.get(device.ip)
            current_status = "Up" if ping and ping.get("is_reachable") else "Down"

            # Check if changed
            last_state = self._last_states.get(str(device.id))
            if not last_state or last_state["status"] != current_status:
                changes.append({
                    "id": str(device.id),
                    "name": device.name,
                    "status": current_status,
                    "changed_at": now.isoformat()
                })

                # Update last state
                self._last_states[str(device.id)] = {
                    "status": current_status,
                    "updated": now
                }

        # Send only changes
        if changes:
            await websocket.send_json({
                "type": "device_updates",
                "changes": changes,
                "timestamp": now.isoformat()
            })
        else:
            # Send heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": now.isoformat()
            })
```

**Expected Impact:**
- 95% reduction in WebSocket bandwidth (437KB → ~2KB per poll)
- Faster frontend updates (less parsing)
- Lower memory usage on clients
- **Effort**: 3-4 hours (frontend + backend changes)
- **Risk**: Medium (requires careful state management)

---

### 9. **Implement VictoriaMetrics Retention Policy**

**Current State:**
- No retention policy configured
- VictoriaMetrics will grow indefinitely
- Currently only 20MB (but will grow)

**Solution:**
```yaml
# docker-compose.production-priority-queues.yml
victoriametrics:
  command:
    - '--storageDataPath=/victoria-metrics-data'
    - '--httpListenAddr=:8428'
    - '--retentionPeriod=90d'  # Keep 3 months (configurable)
    - '--dedup.minScrapeInterval=10s'
```

**Retention Options:**
- **30 days**: ~50MB storage, sufficient for recent analysis
- **90 days**: ~150MB storage, good for quarterly reports
- **365 days**: ~600MB storage, full year of history

**Expected Impact:**
- Predictable storage growth
- Automatic old data cleanup
- Faster queries (less data to scan)
- **Effort**: 5 minutes
- **Risk**: None (choose conservative retention first)

---

### 10. **Add Grafana Dashboards**

**Current State:**
- No visualization of VictoriaMetrics data
- Hard to identify trends and patterns
- No historical analysis tools

**Solution:**
```yaml
# docker-compose.production-priority-queues.yml
grafana:
  image: grafana/grafana:latest
  container_name: wardops-grafana-prod
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    - GF_INSTALL_PLUGINS=grafana-piechart-panel
  volumes:
    - grafana_data:/var/lib/grafana
    - ./grafana/provisioning:/etc/grafana/provisioning
  depends_on:
    - victoriametrics
```

**Dashboards to Create:**

1. **Device Overview**
   - Total devices up/down
   - Uptime percentage by region/branch
   - Top 10 flapping devices

2. **Performance Metrics**
   - Average RTT by device type
   - RTT percentiles (p50, p95, p99)
   - Packet loss trends

3. **Operational Health**
   - VictoriaMetrics ingestion rate
   - Query performance (p95 latency)
   - API response times
   - Worker task queue depth

**Expected Impact:**
- Better visibility into network health
- Identify patterns (e.g., devices always down at night)
- Proactive problem detection
- **Effort**: 4-6 hours (setup + dashboard creation)
- **Risk**: Low (read-only, no production impact)

---

### 11. **Database Connection Pool Optimization**

**Current State:**
```python
# Likely using default SQLAlchemy pool settings
# May be over-provisioned now that VM handles most queries
```

**Analysis Needed:**
```sql
-- Check current connection usage
SELECT
    state,
    COUNT(*),
    MAX(NOW() - state_change) as max_duration,
    AVG(NOW() - state_change) as avg_duration
FROM pg_stat_activity
WHERE datname = 'ward_ops' AND pid != pg_backend_pid()
GROUP BY state
ORDER BY count DESC;
```

**Potential Optimization:**
```python
# database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Reduce from default 50 (VM handles most queries now)
    max_overflow=30,       # Reduce overflow capacity
    pool_timeout=30,
    pool_recycle=3600,     # Recycle connections after 1 hour
    pool_pre_ping=True,    # Verify connections before use
    echo_pool=True         # Log pool events for monitoring
)
```

**Expected Impact:**
- Lower PostgreSQL memory usage
- Faster connection acquisition
- Prevent connection leaks
- **Effort**: 1 hour (measure, adjust, test)
- **Risk**: Low (conservative defaults)

---

### 12. **Implement Structured Logging with ELK Stack**

**Current State:**
- Logs scattered across containers
- Hard to correlate events
- No centralized log search

**Solution:**
```yaml
# docker-compose.production-priority-queues.yml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data

logstash:
  image: docker.elastic.co/logstash/logstash:8.11.0
  volumes:
    - ./logstash/pipeline:/usr/share/logstash/pipeline

kibana:
  image: docker.elastic.co/kibana/kibana:8.11.0
  ports:
    - "5601:5601"
```

```python
# Update logging format to JSON
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)
```

**Expected Impact:**
- Fast log searching (e.g., "all 422 errors in last hour")
- Correlate API errors with worker failures
- Performance trend analysis
- **Effort**: 6-8 hours
- **Risk**: Medium (infrastructure complexity)

---

## 🛠️ TIER 3: FUTURE ENHANCEMENTS

### 13. **GraphQL API for Flexible Queries**

**Benefit:**
- Frontend requests only needed fields
- Reduce payload sizes by 60-70%
- Single endpoint for complex queries

**Example:**
```graphql
query GetDevices {
  devices(filters: {status: "down"}) {
    id
    name
    ip
    downSince
    # Only request what we need!
  }
}
```

**Effort**: 2-3 weeks
**Impact**: Medium-High

---

### 14. **VictoriaMetrics High Availability Setup**

**Current**: Single VictoriaMetrics instance
**Improvement**: Cluster mode with replication

```yaml
# 3-node cluster for redundancy
victoriametrics-1:
  command:
    - '--storageNode'
    - '--replicationFactor=2'

victoriametrics-2:
  # ... same config

victoriametrics-3:
  # ... same config
```

**Benefit:**
- Zero downtime during maintenance
- Data redundancy
- Higher query throughput

**Effort**: 1-2 weeks
**Impact**: High (for production stability)

---

### 15. **Predictive Alerting with ML**

**Concept:**
- Analyze historical ping data patterns
- Predict device failures before they happen
- Alert on anomalies

**Example:**
```python
# Device usually has 2ms RTT, now showing 50ms = early warning
from sklearn.ensemble import IsolationForest

model = train_anomaly_detector(historical_rtt_data)
if model.predict(current_rtt) == -1:
    create_alert("Anomalous RTT detected - potential failure")
```

**Effort**: 3-4 weeks
**Impact**: High (proactive vs reactive monitoring)

---

### 16. **Multi-Region Data Aggregation**

**For Future Expansion:**
- Deploy VictoriaMetrics in each region
- Aggregate data centrally
- Region-specific dashboards

**Effort**: 2-3 weeks
**Impact**: Medium (only if multi-region needed)

---

### 17. **Advanced PromQL Queries for SLA Reporting**

**Examples:**
```promql
# Calculate SLA (99.9% uptime requirement)
avg_over_time(device_ping_status[30d]) * 100 > 99.9

# Monthly uptime report per branch
avg_over_time(device_ping_status[30d]) by (branch) * 100

# Identify flapping devices (up/down > 10 times/day)
changes(device_ping_status[24h]) > 10
```

**Benefit:**
- Automated SLA compliance reports
- Executive dashboards
- Contract validation

**Effort**: 1 week
**Impact**: Medium

---

## RECOMMENDED IMPLEMENTATION ROADMAP

### **Week 1: Quick Wins**
- [ ] Complete Phase 4 (stop PostgreSQL writes) - 5min
- [ ] Fix Redis authentication - 15min
- [ ] Add VM connection pooling - 20min
- [ ] Optimize query resolution (5m/15m/1h) - 15min
- [ ] Add in-memory query cache - 1h
- [ ] Auto-refresh debouncing (frontend) - 2h

**Expected Result:** 90% of requests < 100ms

---

### **Week 2: Data Cleanup**
- [ ] Archive old ping_results data - 5min + 30min runtime
- [ ] Configure VM retention policy (90 days) - 5min
- [ ] Tune database connection pool - 1h
- [ ] Monitor and validate

**Expected Result:** 1.2GB disk space freed

---

### **Week 3-4: Observability**
- [ ] Deploy Grafana - 2h
- [ ] Create device overview dashboard - 2h
- [ ] Create performance dashboard - 2h
- [ ] Create operational health dashboard - 2h
- [ ] Set up alerts in Grafana - 1h

**Expected Result:** Full visibility into system health

---

### **Month 2: Advanced Features**
- [ ] Implement WebSocket delta updates - 4h
- [ ] Set up ELK stack for logging - 8h
- [ ] Create SLA reporting queries - 4h
- [ ] Performance testing and optimization

---

### **Month 3+: Long-term Improvements**
- [ ] Evaluate GraphQL migration
- [ ] Plan VictoriaMetrics HA setup
- [ ] Research predictive alerting
- [ ] Capacity planning for 10,000+ devices

---

## PERFORMANCE TARGETS

### After Tier 1 Optimizations
| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Dashboard load | 30-80ms | <20ms | Redis cache + in-memory cache |
| Device list | 200ms | <50ms | Cache + delta updates |
| Device history (24h) | 1.5s | <200ms | Redis cache + optimized resolution |
| Device history (7d) | 2.5s | <300ms | Reduced data points (15m step) |
| Device history (30d) | 4.5s | <500ms | Reduced data points (1h step) |
| WebSocket update | 360ms | <100ms | In-memory cache + delta updates |
| Cache hit ratio | ~0% | 90%+ | Fix Redis auth |
| Disk growth | Stopped | Stopped | Phase 4 complete |

---

## METRICS TO TRACK

### Application Metrics
```promql
# API response time percentiles
histogram_quantile(0.95, api_request_duration_seconds)

# Cache hit rate
rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])

# VictoriaMetrics query latency
histogram_quantile(0.95, vm_query_duration_seconds)

# WebSocket connection count
websocket_connections_active
```

### Infrastructure Metrics
```promql
# CPU usage
container_cpu_usage_seconds_total

# Memory usage
container_memory_usage_bytes

# Disk I/O
rate(node_disk_io_time_seconds_total[5m])

# Network bandwidth
rate(container_network_transmit_bytes_total[5m])
```

---

## RISK ASSESSMENT

### Low Risk (Do First)
- ✅ Fix Redis auth
- ✅ Add connection pooling
- ✅ Optimize query resolution
- ✅ Add in-memory cache
- ✅ Configure VM retention

### Medium Risk (Test Thoroughly)
- ⚠️ WebSocket delta updates (state management complexity)
- ⚠️ Archive PostgreSQL data (ensure VM has all data first)
- ⚠️ Connection pool tuning (monitor for connection starvation)

### High Risk (Phased Rollout)
- ❌ VictoriaMetrics HA (infrastructure complexity)
- ❌ GraphQL migration (major API change)
- ❌ ELK stack (operational overhead)

---

## SUCCESS CRITERIA

### Week 1 Success
- ✅ 95% of requests complete in < 100ms
- ✅ Redis cache hit rate > 85%
- ✅ Zero HTTP 422 errors from VictoriaMetrics
- ✅ No user-reported slowness

### Month 1 Success
- ✅ Grafana dashboards operational
- ✅ PostgreSQL ping_results table < 100MB
- ✅ VictoriaMetrics storage < 200MB
- ✅ All metrics tracked and alerting configured

### Quarter 1 Success
- ✅ System scales to 2,000+ devices
- ✅ 99.9% API uptime
- ✅ Automated SLA reporting
- ✅ Full observability stack operational

---

## NEXT IMMEDIATE ACTIONS

**Run these commands on production server:**

```bash
# 1. Check current system status
docker ps --format "table {{.Names}}\t{{.Status}}"
docker stats --no-stream

# 2. Check PostgreSQL connection usage
docker exec wardops-postgres-prod psql -U wardops -d ward_ops -c "
SELECT state, COUNT(*),
       MAX(NOW() - state_change) as max_duration
FROM pg_stat_activity
WHERE datname = 'ward_ops'
GROUP BY state;"

# 3. Check VictoriaMetrics stats
curl -s "http://victoriametrics:8428/api/v1/status/tsdb" | jq

# 4. Check Redis connectivity
docker exec wardops-api-prod redis-cli -h redis ping

# 5. Monitor API response times (sample 100 requests)
for i in {1..100}; do
  curl -w "%{time_total}\n" -o /dev/null -s http://localhost:5001/api/v1/dashboard/stats
  sleep 0.5
done | awk '{sum+=$1; count++} END {print "Avg:", sum/count, "seconds"}'
```

---

**Document Status**: Ready for Implementation
**Total Estimated Impact**: 10-20x additional performance improvement
**Total Estimated Effort**: 2-4 weeks for Tier 1, 2-3 months for Tier 2
**Confidence Level**: High (based on architecture analysis and profiling data)
