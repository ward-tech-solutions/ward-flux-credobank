# WARD OPS CredoBank - Optimization Plan

**Goal:** Optimize standalone monitoring system and remove all Zabbix dependencies

**Current State:** 875 devices, 100 workers, ~5-8GB RAM usage

---

## Phase 1: Remove Zabbix Dependencies ✅

### Files to Modify:

1. **`monitoring/models.py`**
   - Remove `MonitoringMode.zabbix` enum value
   - Keep only `standalone` and `snmp_only` modes
   - Remove unused Zabbix-related fields

2. **`monitoring/device_manager.py`**
   - Remove all Zabbix integration code
   - Simplify to standalone-only logic

3. **`routers/devices.py`**
   - Remove Zabbix API calls
   - Remove Zabbix mode checks
   - Simplify to standalone-only endpoints

4. **`routers/dashboard.py`**
   - Remove Zabbix statistics
   - Use standalone device counts only

5. **`monitoring/tasks.py`**
   - Remove Zabbix mode checks
   - Simplify task logic

6. **`main.py`**
   - Remove Zabbix client initialization
   - Remove Zabbix-related state

7. **Delete unused files:**
   - `scripts/import_zabbix_to_standalone.py`
   - Any Zabbix integration modules

### Expected Benefits:
- ✅ Simpler codebase (~30% less code)
- ✅ Faster startup (no Zabbix client init)
- ✅ Easier maintenance
- ✅ No confusion about monitoring modes

---

## Phase 2: Database Optimization 🚀

### Problem:
Currently storing 200 ping results per device = **175,000 total rows** for 875 devices

### Solution: Implement Ping Result Downsampling

**Strategy:**
1. Keep raw ping results for 24 hours (monitoring/alerting)
2. Downsample to 1-minute averages after 24 hours
3. Downsample to 5-minute averages after 7 days
4. Delete data older than 30 days

**Implementation:**

```python
# New table: ping_results_aggregated
CREATE TABLE ping_results_aggregated (
    id SERIAL PRIMARY KEY,
    device_ip VARCHAR(45) NOT NULL,
    device_name VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    interval_minutes INTEGER NOT NULL,  -- 1, 5, 60
    avg_rtt_ms INTEGER,
    min_rtt_ms INTEGER,
    max_rtt_ms INTEGER,
    avg_packet_loss_percent INTEGER,
    samples_count INTEGER,
    uptime_percent DECIMAL(5,2)
);

CREATE INDEX idx_ping_agg_device_time ON ping_results_aggregated(device_ip, timestamp DESC);
```

**Celery Task:**

```python
@shared_task(name="monitoring.tasks.aggregate_ping_results")
def aggregate_ping_results():
    """
    Aggregate ping results to reduce database size

    Runs hourly:
    - Aggregate 1-hour-old data into 1-minute averages
    - Aggregate 7-day-old data into 5-minute averages
    - Delete data older than 30 days
    """
    db = SessionLocal()

    # 1-minute aggregation (data from 1-24 hours ago)
    cutoff_1h = datetime.utcnow() - timedelta(hours=1)
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)

    # Group by device_ip and 1-minute intervals
    aggregated = db.execute(text("""
        INSERT INTO ping_results_aggregated
        (device_ip, device_name, timestamp, interval_minutes,
         avg_rtt_ms, min_rtt_ms, max_rtt_ms, avg_packet_loss_percent,
         samples_count, uptime_percent)
        SELECT
            device_ip,
            device_name,
            date_trunc('minute', timestamp) as minute,
            1 as interval_minutes,
            AVG(avg_rtt_ms)::integer,
            MIN(min_rtt_ms),
            MAX(max_rtt_ms),
            AVG(packet_loss_percent)::integer,
            COUNT(*),
            (SUM(CASE WHEN is_reachable THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::decimal(5,2)
        FROM ping_results
        WHERE timestamp BETWEEN :cutoff_24h AND :cutoff_1h
        AND device_ip NOT IN (
            SELECT DISTINCT device_ip FROM ping_results_aggregated
            WHERE interval_minutes = 1
        )
        GROUP BY device_ip, device_name, date_trunc('minute', timestamp)
    """), {"cutoff_1h": cutoff_1h, "cutoff_24h": cutoff_24h})

    # Delete aggregated raw data
    deleted = db.execute(text("""
        DELETE FROM ping_results
        WHERE timestamp < :cutoff_1h
    """), {"cutoff_1h": cutoff_1h})

    db.commit()
    db.close()

    return {"aggregated": aggregated.rowcount, "deleted": deleted.rowcount}
```

**Expected Benefits:**
- ✅ **80% reduction** in database size (175k → 35k rows)
- ✅ Faster queries (smaller table)
- ✅ Historical data preserved (aggregated)
- ✅ No impact on real-time monitoring

---

## Phase 3: SNMP Optimization 🚀

### Problem:
Currently polling OIDs one-by-one with SNMPv2c GET

### Solution: Implement SNMP GETBULK

**Current Implementation:**
```python
# Polls each OID individually
for item in items:
    result = await snmp_poller.get(device_ip, item.oid, credentials)
    # 10 OIDs = 10 separate SNMP requests
```

**Optimized Implementation:**
```python
# monitoring/snmp/poller.py - Add GETBULK method

async def get_bulk(self, ip: str, oids: List[str], credentials: SNMPCredentialData,
                   port: int = 161, max_repetitions: int = 10) -> Dict[str, SNMPResult]:
    """
    Get multiple OIDs in a single SNMP GETBULK request

    Args:
        ip: Target IP
        oids: List of OIDs to fetch
        credentials: SNMP credentials
        max_repetitions: Number of repetitions per OID

    Returns:
        Dictionary mapping OID to result
    """
    try:
        # Build SNMP GETBULK command
        cmd = BulkCommandGenerator()

        # Convert OID strings to ObjectIdentity objects
        oid_objects = [ObjectIdentity(oid) for oid in oids]

        error_indication, error_status, error_index, var_binds = await cmd.bulkCmd(
            self._get_snmp_engine(credentials),
            CommunityData(credentials.community, mpModel=1),  # SNMPv2c
            UdpTransportTarget((ip, port), timeout=5.0, retries=2),
            ContextData(),
            0,  # non-repeaters
            max_repetitions,  # max-repetitions
            *oid_objects,
            lexicographicMode=False
        )

        if error_indication:
            return {oid: SNMPResult(success=False, error=str(error_indication))
                    for oid in oids}

        # Parse results
        results = {}
        for oid in oids:
            for var_bind_row in var_binds:
                for var_bind in var_bind_row:
                    if str(var_bind[0]) == oid:
                        results[oid] = SNMPResult(
                            success=True,
                            value=str(var_bind[1]),
                            value_type=self._get_value_type(var_bind[1])
                        )

        return results

    except Exception as e:
        return {oid: SNMPResult(success=False, error=str(e)) for oid in oids}
```

**Updated Task:**
```python
@shared_task(bind=True, name="monitoring.tasks.poll_device_snmp")
def poll_device_snmp(self, device_id: str):
    # ... existing setup code ...

    # Collect all OIDs
    oids_to_poll = [item.oid for item in items]

    # BULK poll all OIDs at once (if device supports SNMPv2c)
    if device.snmp_version == "v2c" and len(oids_to_poll) > 1:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            snmp_poller.get_bulk(device_ip, oids_to_poll, credentials, port=snmp_port)
        )
        loop.close()

        # Process results
        for item in items:
            result = results.get(item.oid)
            if result and result.success:
                metrics_to_write.append({
                    "metric_name": _sanitize_metric_name(item.oid_name),
                    "value": float(result.value),
                    "labels": {...}
                })
    else:
        # Fall back to individual GET for SNMPv1 or single OID
        for item in items:
            # ... existing individual polling code ...

    # ... write metrics ...
```

**Expected Benefits:**
- ✅ **50-70% faster** SNMP polling
- ✅ **Reduced network overhead** (1 request vs 10)
- ✅ **Lower CPU usage** on both poller and device
- ✅ **Backwards compatible** (falls back to GET for SNMPv1)

---

## Phase 4: Worker Optimization 🚀

### Problem:
100 workers consuming 5-8GB RAM for 875 devices

### Analysis:

**Current Load:**
- Ping task: ~1s per device
- SNMP task: ~2s per device
- Total work per cycle: 875 devices × 3s = 2,625 seconds
- With 100 workers: 2,625s / 100 = **26.25s per cycle**
- Ping interval: 30s
- SNMP interval: 60s

**Conclusion:** 100 workers is overkill!

### Optimal Worker Count:

**Ping workload (30s interval):**
- 875 devices × 1s = 875s total
- Target: Complete in <25s (buffer for spikes)
- Workers needed: 875s / 25s = **35 workers**

**SNMP workload (60s interval with GETBULK):**
- 875 devices × 1s (optimized) = 875s total
- Target: Complete in <50s
- Workers needed: 875s / 50s = **18 workers**

**Recommendation: 40-50 workers** (handles both workloads + buffer)

### Implementation:

```yaml
# docker-compose.production-local.yml
celery-worker:
  command: celery -A celery_app worker --loglevel=info --concurrency=50
```

**Expected Benefits:**
- ✅ **50% reduction** in RAM usage (8GB → 4GB)
- ✅ **40% reduction** in CPU usage
- ✅ Still handles load with 20% buffer
- ✅ Faster container startup

---

## Phase 5: VictoriaMetrics Recording Rules 🚀

### Problem:
Dashboard queries recalculate metrics every time (CPU intensive)

### Solution: Pre-aggregate Common Metrics

**Create:** `victoriametrics_rules.yml`

```yaml
groups:
  - name: device_metrics
    interval: 60s
    rules:
      # Device uptime percentage (last hour)
      - record: device:uptime:1h
        expr: |
          (sum_over_time(ping_is_alive{job="ward_ops"}[1h]) / count_over_time(ping_is_alive{job="ward_ops"}[1h])) * 100

      # Device uptime percentage (last 24h)
      - record: device:uptime:24h
        expr: |
          (sum_over_time(ping_is_alive{job="ward_ops"}[24h]) / count_over_time(ping_is_alive{job="ward_ops"}[24h])) * 100

      # Average response time (last hour)
      - record: device:rtt_avg:1h
        expr: |
          avg_over_time(ping_rtt_ms{job="ward_ops"}[1h])

      # Device count by region
      - record: region:device_count
        expr: |
          count by (region) (ping_is_alive{job="ward_ops"})

      # Down device count
      - record: ward_ops:devices_down
        expr: |
          count(ping_is_alive{job="ward_ops"} == 0)

      # Total device count
      - record: ward_ops:devices_total
        expr: |
          count(ping_is_alive{job="ward_ops"})

      # CPU usage by device (SNMP)
      - record: device:cpu_usage:5m
        expr: |
          avg_over_time(snmp_cpu_usage{job="ward_ops"}[5m])

      # Memory usage by device (SNMP)
      - record: device:memory_usage:5m
        expr: |
          avg_over_time(snmp_memory_usage{job="ward_ops"}[5m])
```

**Start VictoriaMetrics with rules:**

```bash
# docker-compose.production-local.yml
victoriametrics:
  command:
    - '--storageDataPath=/victoria-metrics-data'
    - '--httpListenAddr=:8428'
    - '--retentionPeriod=12'
    - '--promscrape.config=/etc/victoriametrics/rules.yml'
  volumes:
    - ./victoriametrics_rules.yml:/etc/victoriametrics/rules.yml:ro
```

**Dashboard Queries (Before):**
```promql
# Slow - recalculates every time
(sum_over_time(ping_is_alive{device="ATM-Batumi"}[24h]) / count_over_time(ping_is_alive{device="ATM-Batumi"}[24h])) * 100
```

**Dashboard Queries (After):**
```promql
# Fast - pre-calculated
device:uptime:24h{device="ATM-Batumi"}
```

**Expected Benefits:**
- ✅ **10x faster** dashboard queries
- ✅ **Reduced VM CPU usage** (pre-aggregation)
- ✅ Consistent metric definitions
- ✅ Easier to write queries

---

## Phase 6: Additional Optimizations 🚀

### 6.1 Database Indexing

```sql
-- Add missing indexes for common queries
CREATE INDEX CONCURRENTLY idx_ping_results_device_timestamp
ON ping_results(device_ip, timestamp DESC);

CREATE INDEX CONCURRENTLY idx_standalone_devices_enabled_ip
ON standalone_devices(enabled, ip) WHERE enabled = true;

CREATE INDEX CONCURRENTLY idx_monitoring_items_device_enabled
ON monitoring_items(device_id, enabled) WHERE enabled = true;
```

### 6.2 Connection Pooling

```python
# database.py - Optimize connection pool
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Down from default 50
    max_overflow=10,       # Down from 100
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections every hour
)
```

### 6.3 Celery Task Optimization

```python
# celery_app.py - Optimize task execution
app.conf.update(
    task_acks_late=True,              # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Retry on worker crash
    worker_prefetch_multiplier=2,     # Fetch 2 tasks per worker (down from 4)
    task_time_limit=30,               # Hard limit: 30s per task
    task_soft_time_limit=25,          # Soft limit: 25s per task
)
```

### 6.4 Monitor Page Query Optimization

```typescript
// frontend/src/pages/Monitor.tsx
// Use React Query caching more aggressively

const { data: devices } = useQuery({
  queryKey: ['devices'],
  queryFn: () => devicesAPI.getAll(),
  staleTime: 10_000,        // Consider data fresh for 10s
  cacheTime: 60_000,        // Keep in cache for 1 min
  refetchInterval: 30_000,  // Auto-refresh every 30s
})
```

---

## Implementation Phases

### Week 1: Cleanup & Database
- ✅ Remove all Zabbix code
- ✅ Implement ping result aggregation
- ✅ Add database indexes
- ✅ Test with production data

### Week 2: SNMP & Workers
- ✅ Implement SNMP GETBULK
- ✅ Tune worker count to 50
- ✅ Monitor performance
- ✅ Adjust if needed

### Week 3: VictoriaMetrics
- ✅ Create recording rules
- ✅ Update dashboard queries
- ✅ Verify performance improvement
- ✅ Document new query patterns

### Week 4: Testing & Monitoring
- ✅ Load testing with 1000+ devices
- ✅ Monitor resource usage
- ✅ Fine-tune parameters
- ✅ Document final configuration

---

## Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Database Size (1 month)** | 10 GB | 2 GB | **80% reduction** |
| **RAM Usage** | 8 GB | 4 GB | **50% reduction** |
| **CPU Usage** | 20% | 10% | **50% reduction** |
| **SNMP Poll Time** | 2-3s | 0.5-1s | **60% faster** |
| **Dashboard Load Time** | 2-3s | 0.3-0.5s | **80% faster** |
| **Query Performance** | Slow | Fast | **10x improvement** |
| **Code Complexity** | High | Medium | **30% less code** |

---

## Risk Mitigation

### Backup Strategy:
1. Full database backup before any changes
2. Test aggregation on copy first
3. Keep raw ping data for 24h (rollback window)

### Rollback Plan:
1. Disable aggregation task
2. Restore from backup if needed
3. Revert to 100 workers if load increases

### Monitoring:
1. Track Celery queue length
2. Monitor task completion time
3. Alert if >90% worker utilization
4. Track database growth rate

---

## Next Steps

1. **Review this plan** - Approve phases and timeline
2. **Test environment** - Set up staging with copy of production DB
3. **Phase 1** - Remove Zabbix code (low risk, high benefit)
4. **Phase 2** - Test aggregation on staging
5. **Phase 3** - Implement SNMP GETBULK
6. **Phase 4** - Gradually reduce workers
7. **Phase 5** - Add VictoriaMetrics rules

---

**Estimated Total Time:** 2-3 weeks for all phases

**Estimated ROI:**
- 50% reduction in infrastructure costs
- 80% faster queries
- Simpler codebase
- Better scalability
