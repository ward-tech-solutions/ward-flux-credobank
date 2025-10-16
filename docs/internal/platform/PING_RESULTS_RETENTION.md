# Ping Results Index & Retention Plan

Date: 2025-10-11  
Owner: Platform Hardening

The `ping_results` table now holds ~13K rows from the migration and will continue to grow quickly (every Celery ping inserts a row). To keep read performance predictable and the table size under control, apply the following dual strategy:

## 1. Index Strategy

Current schema ships with single-column indexes on `device_ip` and `timestamp`. To accelerate the hot query patterns (latest status per device, time-ordered history), add a composite index:

```sql
-- Creates an ordered index that supports queries like:
--   SELECT * FROM ping_results WHERE device_ip = ? ORDER BY timestamp DESC LIMIT 1;
CREATE INDEX IF NOT EXISTS idx_ping_results_device_time
  ON ping_results (device_ip, timestamp DESC);
```

Recommended deployment:

1. Run in production with `CREATE INDEX CONCURRENTLY` to avoid table locks:
   ```sql
   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ping_results_device_time
     ON ping_results (device_ip, timestamp DESC);
   ```
2. For local/staging you can run the non-concurrent version (as above) after the migration.
3. Document the index in Alembic/SQL migrations (`migrations/postgres/002_ping_results_indexes.sql`) for automated environments.

## 2. Retention Policy

**Target**: keep the last 90 days of ping telemetry, purge anything older.

The retention job now ships as `maintenance.cleanup_old_ping_results` (see `monitoring/tasks.py`) and is scheduled nightly via `celery_app.py`:

```python
"cleanup-ping-results": {
    "task": "maintenance.cleanup_old_ping_results",
    "schedule": crontab(hour=3, minute=0),
    "kwargs": {"days": 90},
},
```

## 3. Monitoring & Follow-up
- After deploying the index, check `EXPLAIN ANALYZE` on frequent queries to ensure the new index is used.
- Track table size (`SELECT pg_size_pretty(pg_total_relation_size('ping_results'));`) before/after retention runs.
- If telemetry volume grows further, revisit partitioning (monthly partitions by timestamp) before the table reaches tens of millions of rows.
- CI can execute `scripts/celery_smoke_test.py` against a disposable database to verify the cleanup/evaluation tasks.

--- 

Keep this document alongside the backlog (`docs/internal/platform/POSTGRES_MIGRATION_BACKLOG.md`) and update once the index/retention job is merged.***
