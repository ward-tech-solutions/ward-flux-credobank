-- ============================================
-- Alert History Diagnostic Queries
-- ============================================

-- 1. Check the device that shows no alerts (Tsalenjikha-PayBox)
SELECT 
    id,
    name,
    ip,
    ping_status,
    down_since,
    created_at
FROM standalone_devices
WHERE name LIKE '%Tsalenjikha%PayBox%' OR ip = '10.159.43.12';

-- 2. Check if there are ANY alerts for this device
SELECT 
    ah.id,
    ah.device_id,
    ah.rule_name,
    ah.severity,
    ah.message,
    ah.triggered_at,
    ah.resolved_at,
    sd.name as device_name,
    sd.ip as device_ip
FROM alert_history ah
JOIN standalone_devices sd ON ah.device_id = sd.id
WHERE sd.ip = '10.159.43.12' OR sd.name LIKE '%Tsalenjikha%PayBox%'
ORDER BY ah.triggered_at DESC
LIMIT 10;

-- 3. Check alert counts per device (find devices with no alerts)
SELECT 
    sd.id,
    sd.name,
    sd.ip,
    sd.ping_status,
    sd.down_since,
    COUNT(ah.id) as alert_count
FROM standalone_devices sd
LEFT JOIN alert_history ah ON sd.id = ah.device_id
GROUP BY sd.id, sd.name, sd.ip, sd.ping_status, sd.down_since
HAVING COUNT(ah.id) = 0
ORDER BY sd.name
LIMIT 20;

-- 4. Check recent alerts (last 24 hours) - verify alert creation is working
SELECT 
    ah.id,
    ah.rule_name,
    ah.severity,
    ah.message,
    ah.triggered_at,
    ah.resolved_at,
    sd.name as device_name,
    sd.ip as device_ip,
    sd.ping_status
FROM alert_history ah
JOIN standalone_devices sd ON ah.device_id = sd.id
WHERE ah.triggered_at > NOW() - INTERVAL '24 hours'
ORDER BY ah.triggered_at DESC
LIMIT 20;

-- 5. Check DOWN devices that should have alerts
SELECT 
    sd.id,
    sd.name,
    sd.ip,
    sd.ping_status,
    sd.down_since,
    COUNT(ah.id) as active_alert_count
FROM standalone_devices sd
LEFT JOIN alert_history ah ON sd.id = ah.device_id AND ah.resolved_at IS NULL
WHERE sd.ping_status = 'Down' OR sd.down_since IS NOT NULL
GROUP BY sd.id, sd.name, sd.ip, sd.ping_status, sd.down_since
ORDER BY sd.down_since DESC NULLS LAST
LIMIT 20;

-- 6. Check the device that HAS alerts (Marneuli-ATM from first screenshot)
SELECT 
    sd.id,
    sd.name,
    sd.ip,
    sd.ping_status,
    COUNT(ah.id) as total_alerts,
    COUNT(CASE WHEN ah.resolved_at IS NULL THEN 1 END) as active_alerts,
    COUNT(CASE WHEN ah.resolved_at IS NOT NULL THEN 1 END) as resolved_alerts
FROM standalone_devices sd
LEFT JOIN alert_history ah ON sd.id = ah.device_id
WHERE sd.name LIKE '%Marneuli%ATM%'
GROUP BY sd.id, sd.name, sd.ip, sd.ping_status;

-- 7. Show sample alerts from Marneuli-ATM (working device)
SELECT 
    ah.id,
    ah.rule_name,
    ah.severity,
    ah.message,
    ah.triggered_at,
    ah.resolved_at,
    ah.duration_seconds,
    sd.name,
    sd.ip
FROM alert_history ah
JOIN standalone_devices sd ON ah.device_id = sd.id
WHERE sd.name LIKE '%Marneuli%ATM%'
ORDER BY ah.triggered_at DESC
LIMIT 5;

-- 8. Check if monitoring tasks are running (recent ping results)
SELECT 
    sd.name,
    sd.ip,
    sd.ping_status,
    pr.timestamp as last_ping_time,
    pr.is_reachable,
    pr.response_time_ms,
    NOW() - pr.timestamp as time_since_last_ping
FROM standalone_devices sd
LEFT JOIN LATERAL (
    SELECT timestamp, is_reachable, response_time_ms
    FROM ping_results
    WHERE device_id = sd.id
    ORDER BY timestamp DESC
    LIMIT 1
) pr ON true
WHERE sd.ip IN ('10.159.43.12', '10.195.57.5')  -- Compare working vs non-working
ORDER BY sd.name;

-- 9. Count total alerts by type
SELECT 
    rule_name,
    COUNT(*) as count,
    COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as active,
    COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved
FROM alert_history
GROUP BY rule_name
ORDER BY count DESC;

-- 10. Check UUID format consistency (ensure device IDs match)
SELECT 
    'Device UUID Format' as check_type,
    id,
    name,
    LENGTH(id::text) as uuid_length,
    id::text as uuid_string
FROM standalone_devices
WHERE ip = '10.159.43.12'
UNION ALL
SELECT 
    'Alert UUID Format' as check_type,
    device_id as id,
    rule_name as name,
    LENGTH(device_id::text) as uuid_length,
    device_id::text as uuid_string
FROM alert_history
LIMIT 5;

