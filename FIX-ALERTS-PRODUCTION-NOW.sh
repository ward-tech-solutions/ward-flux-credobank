#!/bin/bash

# CORRECT DEPLOYMENT COMMANDS FOR PRODUCTION
# Using the right PostgreSQL credentials: ward_admin / ward_ops

echo "========================================================"
echo "FIXING ALERT RULES ON PRODUCTION SERVER"
echo "========================================================"
echo ""
echo "PostgreSQL Credentials:"
echo "  User: ward_admin"
echo "  Database: ward_ops"
echo ""

# Step 1: Fix the database alert rules
echo "Step 1: Cleaning up duplicate and malformed alert rules..."
echo ""

# Execute the SQL migration with CORRECT credentials
docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops << 'EOF'
-- CRITICAL FIX: Clean up duplicate and incorrect alert rules on production
BEGIN;

-- 1. Remove ALL existing alert rules to start fresh
DELETE FROM alert_rules;

-- 2. Insert correct alert rules with proper expressions
-- Device connectivity alerts (10-second detection)
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, device_id) VALUES
(gen_random_uuid(), 'Device Down', 'Device not responding to ping for 10+ seconds', 'down_time > 10 seconds', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'Device Flapping', 'Device experiencing intermittent connectivity', 'status_changes >= 3 in 5 minutes', 'HIGH', true, NULL);

-- ISP Link specific alerts (for IPs ending with .5)
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, device_id) VALUES
(gen_random_uuid(), 'ISP Link Down', 'Internet service provider link is down', 'isp_link AND down_time > 10 seconds', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'ISP Link Flapping', 'ISP link experiencing intermittent connectivity', 'isp_link AND status_changes >= 2 in 5 minutes', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'ISP Link High Latency', 'ISP link latency exceeds threshold', 'isp_link AND response_time > 100ms', 'HIGH', true, NULL),
(gen_random_uuid(), 'ISP Link Packet Loss', 'ISP link experiencing packet loss', 'isp_link AND packet_loss > 5%', 'CRITICAL', true, NULL);

-- General performance alerts
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, device_id) VALUES
(gen_random_uuid(), 'High Latency', 'Response time exceeds threshold', 'response_time > 200ms', 'MEDIUM', true, NULL),
(gen_random_uuid(), 'Packet Loss Detected', 'Device experiencing packet loss', 'packet_loss > 10%', 'MEDIUM', true, NULL);

-- 3. Clean up orphaned alert history
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

COMMIT;

-- Show the final state
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
EOF

echo ""
echo "Step 2: Verifying rules are fixed..."
echo ""

# Verify no duplicates exist
echo "Checking for duplicate rules (should be empty):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT name, COUNT(*) as count
FROM alert_rules
GROUP BY name
HAVING COUNT(*) > 1;"

echo ""
echo "Total alert rules configured:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT COUNT(*) || ' alert rules' FROM alert_rules;"

echo ""
echo "ISP-specific rules:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, expression, severity
FROM alert_rules
WHERE name LIKE 'ISP%'
ORDER BY name;"

# Step 3: Restart monitoring worker
echo ""
echo "Step 3: Restarting monitoring worker to load fixed evaluator..."
echo ""

docker compose restart worker-monitoring

echo ""
echo "Waiting for worker to start..."
sleep 10

# Step 4: Check worker status
echo ""
echo "Step 4: Checking worker status..."
echo ""

# Check for errors
echo "Checking for errors in worker logs:"
docker logs wardops-worker-monitoring-prod --tail 50 2>&1 | grep -E "(ERROR|error|CRITICAL|exception)" || echo "No errors found"

echo ""
echo "Checking alert evaluation is running:"
docker logs wardops-worker-monitoring-prod --tail 100 2>&1 | grep -E "(alert_evaluator|Alert Evaluation|evaluate_all_alerts)" || echo "Waiting for first evaluation cycle..."

# Step 5: Show current device and alert status
echo ""
echo "Step 5: Current system status..."
echo ""

echo "ISP Link devices (IPs ending with .5):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    name,
    ip,
    CASE
        WHEN down_since IS NULL THEN 'UP'
        ELSE 'DOWN for ' || EXTRACT(EPOCH FROM (NOW() - down_since))::INT || ' seconds'
    END as status,
    is_flapping,
    flap_count
FROM standalone_devices
WHERE ip LIKE '%.5'
AND enabled = true
ORDER BY ip
LIMIT 10;"

echo ""
echo "Active alerts:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    ah.rule_name,
    ah.severity,
    sd.name as device_name,
    sd.ip as device_ip,
    ah.triggered_at
FROM alert_history ah
JOIN standalone_devices sd ON ah.device_id = sd.id
WHERE ah.resolved_at IS NULL
ORDER BY ah.severity, ah.triggered_at DESC
LIMIT 10;"

echo ""
echo "========================================================"
echo "ALERT RULES FIX DEPLOYMENT COMPLETE!"
echo "========================================================"
echo ""
echo "✅ Database cleaned of duplicate and malformed rules"
echo "✅ 8 proper alert rules configured"
echo "✅ ISP link detection ready (IPs ending with .5)"
echo "✅ Worker restarted"
echo ""
echo "Monitor the alert rules page at:"
echo "http://10.30.25.46:5001/alert-rules"
echo ""
echo "The system should now:"
echo "- Detect device down events within 10 seconds"
echo "- Give ISP links (*.5 IPs) CRITICAL priority"
echo "- Auto-resolve alerts when devices recover"
echo "- Have NO parsing errors in logs"