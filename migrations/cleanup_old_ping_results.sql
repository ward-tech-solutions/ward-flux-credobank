-- Clean up old ping results causing 30s query timeouts
--
-- ISSUE: 5,059,463 ping results in database
--        Device details queries timeout after 30s
--        Table grows indefinitely without retention
--
-- FIX: Delete ping results older than 7 days
--      Add index for efficient cleanup
--      Schedule automatic cleanup in celery

-- Count before cleanup
SELECT COUNT(*) as before_count FROM ping_results;

-- Delete ping results older than 7 days
DELETE FROM ping_results
WHERE timestamp < NOW() - INTERVAL '7 days';

-- Count after cleanup
SELECT COUNT(*) as after_count FROM ping_results;

-- Vacuum to reclaim disk space
VACUUM ANALYZE ping_results;

-- Show table size after cleanup
SELECT pg_size_pretty(pg_total_relation_size('ping_results')) as table_size;
