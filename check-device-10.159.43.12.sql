-- Check device 10.159.43.12 specifically

-- 1. Find the device details
SELECT 
    id,
    name,
    ip,
    enabled,
    down_since,
    created_at,
    updated_at
FROM standalone_devices
WHERE ip = '10.159.43.12';

-- 2. Check recent ping results for this device
SELECT 
    pr.device_id,
    pr.timestamp,
    pr.is_reachable,
    pr.latency_ms,
    sd.name,
    sd.ip,
    sd.down_since
FROM ping_results pr
JOIN standalone_devices sd ON pr.device_id = sd.id
WHERE sd.ip = '10.159.43.12'
ORDER BY pr.timestamp DESC
LIMIT 10;

-- 3. Check if there are ANY alerts for this device_id
SELECT 
    ah.*
FROM alert_history ah
WHERE ah.device_id = (SELECT id FROM standalone_devices WHERE ip = '10.159.43.12');

-- 4. Check all DOWN devices and their alert counts
SELECT 
    sd.id,
    sd.name,
    sd.ip,
    sd.down_since,
    sd.enabled,
    COUNT(ah.id) FILTER (WHERE ah.resolved_at IS NULL) as active_alerts,
    COUNT(ah.id) as total_alerts
FROM standalone_devices sd
LEFT JOIN alert_history ah ON sd.id = ah.device_id
WHERE sd.down_since IS NOT NULL
GROUP BY sd.id, sd.name, sd.ip, sd.down_since, sd.enabled
ORDER BY sd.down_since DESC;

-- 5. Check if monitoring is enabled for this device
SELECT 
    id,
    name,
    ip,
    enabled,
    down_since,
    CASE 
        WHEN down_since IS NOT NULL THEN 'DOWN'
        ELSE 'UP'
    END as status,
    EXTRACT(EPOCH FROM (NOW() - down_since))/60 as minutes_down
FROM standalone_devices
WHERE ip = '10.159.43.12';
