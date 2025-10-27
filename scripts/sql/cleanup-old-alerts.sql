-- ============================================================================
-- Clean Up Old Resolved Alerts (Older Than 7 Days)
-- ============================================================================
--
-- PURPOSE: Remove old resolved alerts to keep database lean
--
-- RETENTION POLICY:
-- - Keep all UNRESOLVED alerts (regardless of age)
-- - Delete RESOLVED alerts older than 7 days
-- - Keep statistics for last 7 days
--
-- BEFORE CLEANUP:
-- - Check how many alerts will be deleted
-- - Verify no unresolved alerts will be touched
--
-- ============================================================================

-- Step 1: Show current alert statistics
SELECT
    COUNT(*) as total_alerts,
    COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as unresolved,
    COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved,
    COUNT(CASE WHEN resolved_at < NOW() - INTERVAL '7 days' THEN 1 END) as resolved_older_than_7d
FROM alert_history;

-- Step 2: Show disk space used by alert_history table
SELECT
    pg_size_pretty(pg_total_relation_size('alert_history')) as total_size,
    pg_size_pretty(pg_relation_size('alert_history')) as table_size,
    pg_size_pretty(pg_indexes_size('alert_history')) as indexes_size;

-- Step 3: Preview what will be deleted
SELECT
    DATE(resolved_at) as date,
    COUNT(*) as alerts_to_delete
FROM alert_history
WHERE resolved_at IS NOT NULL
AND resolved_at < NOW() - INTERVAL '7 days'
GROUP BY DATE(resolved_at)
ORDER BY date;

-- Step 4: Delete old resolved alerts (EXECUTE THIS STEP)
-- IMPORTANT: Only deletes RESOLVED alerts older than 7 days
DELETE FROM alert_history
WHERE resolved_at IS NOT NULL
AND resolved_at < NOW() - INTERVAL '7 days';

-- Step 5: Show statistics after cleanup
SELECT
    COUNT(*) as total_alerts_remaining,
    COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as unresolved,
    COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved_last_7d
FROM alert_history;

-- Step 6: Show disk space saved
SELECT
    pg_size_pretty(pg_total_relation_size('alert_history')) as total_size_after,
    pg_size_pretty(pg_relation_size('alert_history')) as table_size_after,
    pg_size_pretty(pg_indexes_size('alert_history')) as indexes_size_after;

-- Step 7: Vacuum to reclaim disk space
VACUUM FULL ANALYZE alert_history;

-- ============================================================================
-- AUTOMATION: Add to Celery Beat Schedule
-- ============================================================================
--
-- To run this cleanup automatically every week, add to celery_app.py:
--
-- 'cleanup-old-alerts': {
--     'task': 'maintenance.cleanup_old_alerts',
--     'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
-- }
--
-- ============================================================================
