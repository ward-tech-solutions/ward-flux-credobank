-- ============================================================================
-- FIX: Alert Auto-Resolution Bug
-- ============================================================================
--
-- PROBLEM: Old alerts have rule_id = NULL, so they never get auto-resolved
--
-- ROOT CAUSE:
-- 1. tasks_batch.py created alerts with rule_id = NULL
-- 2. evaluate_alert_rules() queries: WHERE rule_id = :rule_id
-- 3. NULL != :rule_id in SQL, so query doesn't find old alerts
-- 4. Auto-resolution logic never triggers
--
-- SOLUTION:
-- 1. Map rule names to rule IDs
-- 2. Update all NULL rule_id values with correct IDs
-- 3. Future alerts will use rule_name matching as fallback
-- ============================================================================

-- Step 1: Show current state
SELECT
    COUNT(*) as total_alerts,
    COUNT(rule_id) as with_rule_id,
    COUNT(*) - COUNT(rule_id) as null_rule_id,
    COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as unresolved
FROM alert_history;

-- Step 2: Show unresolved alerts with NULL rule_id
SELECT
    rule_name,
    severity,
    COUNT(*) as count,
    MIN(triggered_at) as oldest,
    MAX(triggered_at) as newest
FROM alert_history
WHERE rule_id IS NULL
AND resolved_at IS NULL
GROUP BY rule_name, severity
ORDER BY count DESC;

-- Step 3: Update rule_id based on rule_name matching
-- Match "Ping Unavailable" alerts
UPDATE alert_history ah
SET rule_id = ar.id
FROM alert_rules ar
WHERE ah.rule_id IS NULL
AND ah.rule_name = 'Ping Unavailable'
AND ar.name = 'Ping Unavailable';

-- Match "Device Down - High Priority" alerts
UPDATE alert_history ah
SET rule_id = ar.id
FROM alert_rules ar
WHERE ah.rule_id IS NULL
AND ah.rule_name = 'Device Down - High Priority'
AND ar.name = 'Device Down - High Priority';

-- Match "Device Down - Critical" alerts
UPDATE alert_history ah
SET rule_id = ar.id
FROM alert_rules ar
WHERE ah.rule_id IS NULL
AND ah.rule_name = 'Device Down - Critical'
AND ar.name = 'Device Down - Critical';

-- Match "High Latency" alerts
UPDATE alert_history ah
SET rule_id = ar.id
FROM alert_rules ar
WHERE ah.rule_id IS NULL
AND ah.rule_name = 'High Latency'
AND ar.name = 'High Latency';

-- Step 4: Verify fix
SELECT
    COUNT(*) as total_alerts,
    COUNT(rule_id) as with_rule_id,
    COUNT(*) - COUNT(rule_id) as null_rule_id_remaining
FROM alert_history;

-- Step 5: Show which devices have unresolved alerts now
SELECT
    sd.name,
    sd.ip,
    ah.rule_name,
    ah.severity,
    ah.triggered_at,
    NOW() - ah.triggered_at as age
FROM alert_history ah
JOIN standalone_devices sd ON ah.device_id = sd.id
WHERE ah.resolved_at IS NULL
ORDER BY ah.triggered_at DESC
LIMIT 20;
