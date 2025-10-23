-- ============================================================================
-- WARD OPS - Device Details Performance Optimization
-- Add indexes to alert_history table for faster device details loading
-- ============================================================================

-- Issue: Device details modal takes 12+ seconds to load
-- Root Cause: Slow queries on alert_history table
-- Solution: Add composite indexes for common query patterns

-- Expected Impact:
-- - Device alerts query: 500ms → 50ms (10x faster)
-- - Device details modal load: 13s → 1-2s (10x faster)

\echo '==================================================================='
\echo 'Adding alert_history performance indexes...'
\echo '==================================================================='

-- 1. Composite index for device_id + triggered_at DESC
-- Used by: GET /alerts?device_id={id}&limit=50
-- Query pattern: WHERE device_id = ? ORDER BY triggered_at DESC LIMIT ?
CREATE INDEX IF NOT EXISTS idx_alert_history_device_triggered
    ON alert_history(device_id, triggered_at DESC);

\echo '✓ Created idx_alert_history_device_triggered'

-- 2. Composite index for device_id + resolved_at (for status filtering)
-- Used by: GET /alerts?device_id={id}&status=active
-- Query pattern: WHERE device_id = ? AND resolved_at IS NULL
CREATE INDEX IF NOT EXISTS idx_alert_history_device_resolved
    ON alert_history(device_id, resolved_at);

\echo '✓ Created idx_alert_history_device_resolved'

-- 3. Composite index for severity + triggered_at DESC
-- Used by: GET /alerts?severity=critical ORDER BY triggered_at DESC
-- Query pattern: WHERE severity = ? ORDER BY triggered_at DESC
CREATE INDEX IF NOT EXISTS idx_alert_history_severity_triggered
    ON alert_history(severity, triggered_at DESC);

\echo '✓ Created idx_alert_history_severity_triggered'

-- 4. Index on triggered_at for general sorting
-- Used by: GET /alerts ORDER BY triggered_at DESC
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered
    ON alert_history(triggered_at DESC);

\echo '✓ Created idx_alert_history_triggered'

\echo ''
\echo '==================================================================='
\echo 'Verifying indexes...'
\echo '==================================================================='

-- Show all indexes on alert_history table
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'alert_history'
ORDER BY indexname;

\echo ''
\echo '==================================================================='
\echo 'Index sizes:'
\echo '==================================================================='

-- Show index sizes
SELECT
    indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND relname = 'alert_history'
ORDER BY pg_relation_size(indexrelid) DESC;

\echo ''
\echo '==================================================================='
\echo '✓ Alert history indexes created successfully!'
\echo '==================================================================='
\echo ''
\echo 'Expected improvements:'
\echo '  • Device alerts query: 10x faster'
\echo '  • Device details modal: Loads in 1-2 seconds (was 13+ seconds)'
\echo '  • Redis caching: 30-second TTL for subsequent loads'
\echo ''
