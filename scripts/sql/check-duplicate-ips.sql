-- Find duplicate IP addresses in standalone_devices table
-- This query shows which IPs are used by multiple devices

SELECT
    ip,
    COUNT(*) as device_count,
    STRING_AGG(name, ', ') as device_names,
    STRING_AGG(CAST(id AS TEXT), ', ') as device_ids
FROM standalone_devices
GROUP BY ip
HAVING COUNT(*) > 1
ORDER BY device_count DESC, ip;

-- Additional analysis: Show full details of duplicate IP devices
SELECT
    d.ip,
    d.id,
    d.name,
    d.normalized_name,
    d.device_type,
    d.enabled,
    b.display_name as branch_name,
    d.created_at
FROM standalone_devices d
LEFT JOIN branches b ON d.branch_id = b.id
WHERE d.ip IN (
    SELECT ip
    FROM standalone_devices
    GROUP BY ip
    HAVING COUNT(*) > 1
)
ORDER BY d.ip, d.created_at;
