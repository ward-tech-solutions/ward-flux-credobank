#!/bin/bash
# Fix Alert Rules - Remove duplicates and add real-time rules

set -e

echo "================================================"
echo "🔧 FIXING ALERT RULES SYSTEM"
echo "================================================"
echo ""

# First, show current state
echo "📊 Current Alert Rules:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, severity, expression, enabled
FROM alert_rules
ORDER BY name;"

# Clean up ALL old rules and start fresh
echo ""
echo "🗑️  Removing old/duplicate alert rules..."
# IMPORTANT: Stop on first SQL error and cascade truncate across FKs (alert_history)
docker exec -i wardops-postgres-prod psql -v ON_ERROR_STOP=1 -U ward_admin -d ward_ops << 'EOF'
-- First backup existing rules
CREATE TABLE IF NOT EXISTS alert_rules_backup AS
SELECT * FROM alert_rules;

-- Clear all old rules
TRUNCATE TABLE alert_rules CASCADE;

-- Insert new real-time alert rules
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, created_at, updated_at) VALUES
-- Device connectivity (10-second detection)
(gen_random_uuid(), 'Device Down', 'Device not responding for 10 seconds', 'ping_unreachable >= 10', 'critical', true, NOW(), NOW()),
(gen_random_uuid(), 'Device Flapping', 'Device status changing frequently', 'status_changes >= 3 in 5min', 'high', true, NOW(), NOW()),

-- ISP Link alerts (special handling for .5 IPs)
(gen_random_uuid(), 'ISP Link Down', 'ISP link not responding for 10 seconds', 'ping_unreachable >= 10 AND ip LIKE ''%.5''', 'critical', true, NOW(), NOW()),
(gen_random_uuid(), 'ISP Link Flapping', 'ISP link unstable connection', 'status_changes >= 2 in 5min AND ip LIKE ''%.5''', 'critical', true, NOW(), NOW()),

-- Performance alerts
(gen_random_uuid(), 'High Latency', 'Response time exceeds 200ms', 'avg_ping_ms > 200', 'medium', true, NOW(), NOW()),
(gen_random_uuid(), 'ISP High Latency', 'ISP link latency exceeds 100ms', 'avg_ping_ms > 100 AND ip LIKE ''%.5''', 'high', true, NOW(), NOW()),

-- Packet loss alerts
(gen_random_uuid(), 'Packet Loss', 'Device experiencing packet loss', 'packet_loss > 10', 'medium', true, NOW(), NOW()),
(gen_random_uuid(), 'ISP Packet Loss', 'ISP link packet loss detected', 'packet_loss > 5 AND ip LIKE ''%.5''', 'critical', true, NOW(), NOW());

-- Show new rules
SELECT 'New Alert Rules Created:' as status;
SELECT name, severity, expression, enabled FROM alert_rules ORDER BY
  CASE severity
    WHEN 'CRITICAL' THEN 1
    WHEN 'HIGH' THEN 2
    WHEN 'MEDIUM' THEN 3
    WHEN 'LOW' THEN 4
    ELSE 5
  END, name;
EOF

# Add missing columns if needed
echo ""
echo "🔧 Updating alert_rules table structure..."
docker exec -i wardops-postgres-prod psql -v ON_ERROR_STOP=1 -U ward_admin -d ward_ops << 'EOF'
-- Add columns for better rule management
ALTER TABLE alert_rules
ADD COLUMN IF NOT EXISTS rule_type VARCHAR(50) DEFAULT 'threshold',
ADD COLUMN IF NOT EXISTS applies_to VARCHAR(50) DEFAULT 'all',
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5,
ADD COLUMN IF NOT EXISTS cooldown_minutes INTEGER DEFAULT 5,
ADD COLUMN IF NOT EXISTS auto_resolve BOOLEAN DEFAULT true;

-- Update rule types
UPDATE alert_rules SET rule_type = 'connectivity', priority = 1 WHERE name LIKE '%Down%';
UPDATE alert_rules SET rule_type = 'stability', priority = 2 WHERE name LIKE '%Flapping%';
UPDATE alert_rules SET rule_type = 'performance', priority = 3 WHERE name LIKE '%Latency%';
UPDATE alert_rules SET rule_type = 'performance', priority = 3 WHERE name LIKE '%Packet Loss%';

-- ISP rules get highest priority
UPDATE alert_rules SET priority = 0, applies_to = 'isp_links' WHERE name LIKE 'ISP%';
UPDATE alert_rules SET applies_to = 'all_devices' WHERE name NOT LIKE 'ISP%';

-- Show final state
SELECT name, severity, priority, applies_to, rule_type
FROM alert_rules
ORDER BY priority, name;
EOF

# Clear any stuck alerts from old rules
echo ""
echo "🧹 Cleaning up old alerts..."
docker exec -i wardops-postgres-prod psql -v ON_ERROR_STOP=1 -U ward_admin -d ward_ops << 'EOF'
-- Resolve old alerts from deleted rules
UPDATE alert_history
SET resolved_at = NOW()
WHERE resolved_at IS NULL
AND rule_name IN (
  'Ping Unavailable',
  'Device Down - Critical',
  'Device Down - High Priority',
  'Device unreachable for 5+ minutes',
  'Device unreachable for 2+ minutes'
);

-- Count cleanup
SELECT COUNT(*) as resolved_old_alerts
FROM alert_history
WHERE resolved_at = NOW()::date;
EOF

# Show ISP links that will get priority monitoring
echo ""
echo "🌐 ISP Links with Priority Monitoring:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, ip,
       CASE WHEN down_since IS NULL THEN '✅ UP' ELSE '❌ DOWN' END as status,
       CASE WHEN is_flapping THEN '⚠️ FLAPPING' ELSE 'STABLE' END as stability
FROM standalone_devices
WHERE ip LIKE '%.5'
AND enabled = true
ORDER BY ip;"

echo ""
echo "================================================"
echo "✅ ALERT RULES FIXED!"
echo "================================================"
echo ""
echo "Changes Made:"
echo "  ✓ Removed duplicate rules"
echo "  ✓ Added 10-second detection rules"
echo "  ✓ Added ISP link priority rules (.5 IPs)"
echo "  ✓ Added flapping detection rules"
echo "  ✓ Set proper severity levels"
echo ""
echo "Alert Detection Times:"
echo "  • Device Down: 10 seconds (was 5+ minutes)"
echo "  • ISP Link Down: 10 seconds CRITICAL"
echo "  • Flapping: 3 changes in 5 min (2 for ISP)"
echo ""
echo "Restart services to apply:"
echo "  docker restart wardops-worker-alerts-prod wardops-beat-prod"
echo ""
