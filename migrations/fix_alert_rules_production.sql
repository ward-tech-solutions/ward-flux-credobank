-- CRITICAL FIX: Clean up duplicate and incorrect alert rules on production
-- This fixes the parsing errors and duplicate rules found in production

BEGIN;

-- 1. Remove ALL existing alert rules to start fresh
-- We need clean slate because of duplicate and malformed rules
DELETE FROM alert_rules;

-- 2. Insert correct alert rules with proper expressions
-- Note: These expressions are for display only, actual logic is in Python code

-- Device connectivity alerts (10-second detection)
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, device_id) VALUES
(gen_random_uuid(), 'Device Down', 'Device not responding to ping for 10+ seconds', 'down_time > 10 seconds', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'Device Flapping', 'Device experiencing intermittent connectivity', 'status_changes >= 3 in 5 minutes', 'HIGH', true, NULL);

-- ISP Link specific alerts (for IPs ending with .5)
-- These use simplified expressions - actual ISP detection is in Python code
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, device_id) VALUES
(gen_random_uuid(), 'ISP Link Down', 'Internet service provider link is down', 'isp_link AND down_time > 10 seconds', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'ISP Link Flapping', 'ISP link experiencing intermittent connectivity', 'isp_link AND status_changes >= 2 in 5 minutes', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'ISP Link High Latency', 'ISP link latency exceeds threshold', 'isp_link AND response_time > 100ms', 'HIGH', true, NULL),
(gen_random_uuid(), 'ISP Link Packet Loss', 'ISP link experiencing packet loss', 'isp_link AND packet_loss > 5%', 'CRITICAL', true, NULL);

-- General performance alerts
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, device_id) VALUES
(gen_random_uuid(), 'High Latency', 'Response time exceeds threshold', 'response_time > 200ms', 'MEDIUM', true, NULL),
(gen_random_uuid(), 'Packet Loss Detected', 'Device experiencing packet loss', 'packet_loss > 10%', 'MEDIUM', true, NULL);

-- 3. Clean up orphaned alert history (alerts with rules that no longer exist)
DELETE FROM alert_history
WHERE rule_name NOT IN (
    'Device Down',
    'Device Flapping',
    'ISP Link Down',
    'ISP Link Flapping',
    'ISP Link High Latency',
    'ISP Link Packet Loss',
    'High Latency',
    'Packet Loss Detected'
);

-- 4. Update any active alerts to use correct rule names
UPDATE alert_history
SET rule_name = 'Device Down'
WHERE rule_name IN ('Ping Unavailable', 'Device Down - Critical', 'Device Down - High Priority')
AND resolved_at IS NULL;

-- 5. Show the final state
SELECT name, description, expression, severity, enabled
FROM alert_rules
ORDER BY
    CASE severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        ELSE 4
    END,
    name;

COMMIT;

-- Verify no duplicates exist
SELECT name, COUNT(*) as count
FROM alert_rules
GROUP BY name
HAVING COUNT(*) > 1;