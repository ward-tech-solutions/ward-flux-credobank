# Ping Results Retention Configuration

## Current Configuration

**Retention Period:** 30 days
**Cleanup Schedule:** Daily at 3 AM
**Configuration File:** [monitoring/celery_app.py](monitoring/celery_app.py#L85-L89)

```python
"cleanup-ping-results": {
    "task": "maintenance.cleanup_old_ping_results",
    "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    "kwargs": {"days": 30},  # Keep 30 days of data
}
```

---

## Data Growth Analysis

For **875 devices** with ping **every 30 seconds**:

| Retention | Total Pings | Rows in DB | Disk Space | Query Speed |
|-----------|-------------|------------|------------|-------------|
| **7 days** | 17,640,000 | ~18M rows | ~1.2 GB | ⚡ Very Fast |
| **14 days** | 35,280,000 | ~35M rows | ~2.4 GB | ⚡ Very Fast |
| **30 days** | 75,600,000 | ~76M rows | ~5 GB | 🟢 Fast |
| **60 days** | 151,200,000 | ~151M rows | ~10 GB | 🟡 Moderate |
| **90 days** | 226,800,000 | ~227M rows | ~15 GB | 🟠 Slow |
| **180 days** | 453,600,000 | ~454M rows | ~30 GB | 🔴 Very Slow |
| **365 days** | 927,450,000 | ~927M rows | ~61 GB | 💀 Too Slow |

**Calculation:**
- Pings per day: 875 devices × (86400 seconds / 30 seconds) = 2,520,000 pings/day
- Pings per month (30 days): 2,520,000 × 30 = 75,600,000 pings

---

## Retention Options

### Option 1: 30 Days (Recommended - Current Setting)

**Best for:** Production monitoring with recent history

**Pros:**
- ✅ 5GB disk space (manageable)
- ✅ Fast queries even without indexes
- ✅ Covers most troubleshooting scenarios
- ✅ Enough data for trend analysis
- ✅ Meets most compliance requirements

**Cons:**
- ❌ Historical data beyond 1 month lost
- ❌ Cannot analyze long-term trends

**Use Cases:**
- Real-time monitoring
- Recent downtime investigation
- Performance trend analysis (last month)
- Alerting and troubleshooting

---

### Option 2: 60 Days

**Best for:** Extended historical analysis

**Pros:**
- ✅ 2 months of data for trend analysis
- ✅ Better for quarterly reporting
- ✅ Still reasonably fast queries

**Cons:**
- ❌ 10GB disk space required
- ❌ Queries slower with 150M+ rows
- ❌ Requires more database tuning

**Configuration:**
```python
"kwargs": {"days": 60},  # Keep 60 days
```

---

### Option 3: 90 Days

**Best for:** Quarterly compliance reporting

**Pros:**
- ✅ Full quarterly data available
- ✅ Better for long-term analysis

**Cons:**
- ❌ 15GB disk space
- ❌ Significantly slower queries
- ❌ Requires aggressive indexing
- ❌ Cleanup takes longer

**Configuration:**
```python
"kwargs": {"days": 90},  # Keep 90 days
```

---

### Option 4: 7 Days (Minimal)

**Best for:** Low disk space environments or very high device count

**Pros:**
- ✅ Only 1.2GB disk space
- ✅ Extremely fast queries
- ✅ Minimal cleanup time

**Cons:**
- ❌ Very limited historical data
- ❌ Cannot investigate issues from last week
- ❌ Not suitable for reporting

**Configuration:**
```python
"kwargs": {"days": 7},  # Keep 7 days
```

---

## Alternative: PostgreSQL Table Partitioning

For retention > 60 days, consider **table partitioning by month**:

### Benefits:
- ✅ Fast queries (only search relevant partitions)
- ✅ Easy cleanup (drop entire partition)
- ✅ Better performance with huge datasets
- ✅ Can keep 1+ year of data efficiently

### Setup Example:

```sql
-- Convert ping_results to partitioned table
CREATE TABLE ping_results_new (
    LIKE ping_results INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE ping_results_2025_10 PARTITION OF ping_results_new
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE ping_results_2025_11 PARTITION OF ping_results_new
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- Migrate data
INSERT INTO ping_results_new SELECT * FROM ping_results;

-- Swap tables
DROP TABLE ping_results;
ALTER TABLE ping_results_new RENAME TO ping_results;
```

**Cleanup becomes simple:**
```sql
-- Drop entire October 2024 partition (instant!)
DROP TABLE ping_results_2024_10;
```

---

## Hybrid Approach: Aggregation

Keep **detailed data for 30 days**, then **aggregate older data**:

### Strategy:
1. Keep full resolution for last 30 days (every 30s)
2. Aggregate 30-90 days to 5-minute intervals
3. Aggregate 90-365 days to 1-hour intervals
4. Delete data > 1 year

### Benefits:
- ✅ Fast recent queries
- ✅ Long-term trend analysis still possible
- ✅ Much less disk space
- ✅ Faster queries on old data

### Implementation:
```python
# Create aggregated_ping_results table
CREATE TABLE aggregated_ping_results (
    device_ip VARCHAR(50),
    hour_bucket TIMESTAMP,
    avg_rtt_ms INTEGER,
    max_rtt_ms INTEGER,
    packet_loss_percent INTEGER,
    total_pings INTEGER,
    successful_pings INTEGER
);

# Aggregate and move old data (run monthly)
INSERT INTO aggregated_ping_results
SELECT
    device_ip,
    date_trunc('hour', timestamp) as hour_bucket,
    AVG(avg_rtt_ms)::INTEGER as avg_rtt_ms,
    MAX(max_rtt_ms) as max_rtt_ms,
    AVG(packet_loss_percent)::INTEGER as packet_loss_percent,
    COUNT(*) as total_pings,
    SUM(CASE WHEN is_reachable THEN 1 ELSE 0 END) as successful_pings
FROM ping_results
WHERE timestamp < NOW() - INTERVAL '30 days'
  AND timestamp >= NOW() - INTERVAL '60 days'
GROUP BY device_ip, hour_bucket;

# Delete raw data that was aggregated
DELETE FROM ping_results
WHERE timestamp < NOW() - INTERVAL '30 days';
```

---

## How to Change Retention Period

### Method 1: Edit celery_app.py (Requires Restart)

1. Edit [monitoring/celery_app.py](monitoring/celery_app.py):
```python
"cleanup-ping-results": {
    "task": "maintenance.cleanup_old_ping_results",
    "schedule": crontab(hour=3, minute=0),
    "kwargs": {"days": 60},  # Change from 30 to 60
}
```

2. Rebuild and restart:
```bash
docker-compose -f docker-compose.production-local.yml down
docker-compose -f docker-compose.production-local.yml build celery-beat
docker-compose -f docker-compose.production-local.yml up -d
```

---

### Method 2: Manual Cleanup (One-Time)

Run cleanup manually with custom retention:

```bash
# Clean up data older than 60 days (one-time)
docker exec wardops-worker-prod celery -A celery_app call \
    maintenance.cleanup_old_ping_results \
    --kwargs='{"days": 60}'
```

---

### Method 3: Change Cleanup Schedule

To clean up more frequently (reduce disk spikes):

```python
# Run every 12 hours instead of daily
"cleanup-ping-results": {
    "task": "maintenance.cleanup_old_ping_results",
    "schedule": crontab(hour='*/12', minute=0),  # Every 12 hours
    "kwargs": {"days": 30},
}

# Run every 6 hours
"schedule": crontab(hour='*/6', minute=0),  # Every 6 hours
```

---

## Monitoring Ping Results Table

### Check Current Table Size
```bash
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    pg_size_pretty(pg_total_relation_size('ping_results')) as total_size,
    pg_size_pretty(pg_relation_size('ping_results')) as table_size,
    pg_size_pretty(pg_indexes_size('ping_results')) as indexes_size,
    (SELECT count(*) FROM ping_results) as row_count,
    (SELECT min(timestamp) FROM ping_results) as oldest_record,
    (SELECT max(timestamp) FROM ping_results) as newest_record;
"
```

### Check Cleanup History
```bash
docker logs wardops-worker-prod 2>&1 | grep "Removed.*ping_results"
```

### Estimated Time to Fill Disk
```bash
# Get current table growth rate
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    current_setting('data_directory') as data_dir,
    pg_size_pretty(sum(pg_database_size(datname))) as total_db_size
FROM pg_database
WHERE datname = 'ward_ops';
"
```

---

## Recommendations

### For CredoBank (875 Devices):

**Recommended:** **30 days retention** (current setting)

**Reasoning:**
- ✅ Covers most troubleshooting needs
- ✅ Manageable disk space (5GB)
- ✅ Fast query performance
- ✅ Sufficient for trend analysis
- ✅ Meets typical compliance requirements

**If you need longer history:**
- Use **partitioning** for > 90 days
- Use **aggregation** for trend analysis beyond 30 days
- Export old data to CSV/archive before deletion

### Disk Space Planning:

| Retention | Disk Space | Free Space Needed |
|-----------|------------|-------------------|
| 30 days | 5 GB | 15 GB (3× safety factor) |
| 60 days | 10 GB | 30 GB |
| 90 days | 15 GB | 45 GB |

**Monitor disk space:**
```bash
df -h | grep -E "Filesystem|/var/lib/docker"
```

---

## Next Steps After Changing Retention

1. **Wait for first cleanup** (runs at 3 AM)
2. **Monitor disk space** for 7 days
3. **Verify query performance** remains acceptable
4. **Check cleanup logs** to ensure deletion happening
5. **Adjust if needed**

---

**Configuration:** [monitoring/celery_app.py](monitoring/celery_app.py#L85-L89)
**Cleanup Task:** [monitoring/tasks.py](monitoring/tasks.py#L775-L796)
**Cleanup Time:** Daily at 3 AM UTC
**Current Retention:** 30 days
