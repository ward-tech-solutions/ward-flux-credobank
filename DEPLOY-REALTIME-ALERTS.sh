#!/bin/bash
# Deploy Real-time Alert System with ISP Link Monitoring
# 10-second detection for all alerts, priority for ISP links

set -e

echo "=========================================="
echo "🚨 DEPLOYING REAL-TIME ALERT SYSTEM"
echo "=========================================="
echo ""
echo "Features:"
echo "  ✓ 10-second alert detection (not 5 minutes!)"
echo "  ✓ ISP Link monitoring (IPs ending with .5)"
echo "  ✓ Flapping detection with alert suppression"
echo "  ✓ Duplicate alert cleanup"
echo "  ✓ Priority queues for critical alerts"
echo ""

# Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# Show ISP links that will be monitored
echo ""
echo "🌐 ISP Links to monitor (IPs ending with .5):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, ip,
       CASE WHEN down_since IS NULL THEN 'UP' ELSE 'DOWN' END as status
FROM standalone_devices
WHERE ip LIKE '%.5' AND enabled = true
ORDER BY ip;"

# Clean up duplicate alerts
echo ""
echo "🧹 Cleaning up duplicate alert rules..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops << 'EOF'
-- Show current alert rules
SELECT 'Current alert rules:' as info;
SELECT name, COUNT(*) as count
FROM alert_rules
GROUP BY name
HAVING COUNT(*) > 1;

-- Remove duplicates (keep first)
WITH duplicates AS (
    SELECT id, name,
           ROW_NUMBER() OVER (PARTITION BY name ORDER BY created_at) as rn
    FROM alert_rules
)
DELETE FROM alert_rules
WHERE id IN (
    SELECT id FROM duplicates WHERE rn > 1
);

-- Add missing columns if needed
ALTER TABLE alert_rules
ADD COLUMN IF NOT EXISTS rule_name VARCHAR(200),
ADD COLUMN IF NOT EXISTS threshold_value NUMERIC,
ADD COLUMN IF NOT EXISTS threshold_condition VARCHAR(50);

SELECT 'Alert rules after cleanup:' as info;
SELECT name, severity, enabled FROM alert_rules;
EOF

# Build and deploy
echo ""
echo "🔨 Building containers..."
docker-compose -f docker-compose.production-priority-queues.yml build api celery-worker-monitoring celery-worker-alerts celery-beat

echo ""
echo "🛑 Stopping old services..."
docker stop wardops-api-prod wardops-worker-monitoring-prod wardops-worker-alerts-prod wardops-beat-prod || true

echo ""
echo "🗑️ Removing old containers..."
docker rm wardops-api-prod wardops-worker-monitoring-prod wardops-worker-alerts-prod wardops-beat-prod || true

echo ""
echo "🚀 Starting new services..."
docker-compose -f docker-compose.production-priority-queues.yml up -d

# Wait for startup
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Test alert system
echo ""
echo "🧪 Testing alert system..."
python3 << 'EOF'
import psycopg2
from datetime import datetime

print("\n📊 Alert System Status:")
print("-" * 50)

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="ward_ops",
    user="ward_admin",
    password="ward_admin_password"
)
cur = conn.cursor()

# Check ISP links
cur.execute("""
    SELECT COUNT(*) FROM standalone_devices
    WHERE ip LIKE '%.5' AND enabled = true
""")
isp_count = cur.fetchone()[0]
print(f"ISP Links monitored: {isp_count}")

# Check flapping devices
cur.execute("""
    SELECT COUNT(*) FROM standalone_devices
    WHERE is_flapping = true
""")
flapping_count = cur.fetchone()[0]
print(f"Devices currently flapping: {flapping_count}")

# Check active alerts
cur.execute("""
    SELECT rule_name, COUNT(*) as count
    FROM alert_history
    WHERE resolved_at IS NULL
    GROUP BY rule_name
    ORDER BY count DESC
""")
alerts = cur.fetchall()
if alerts:
    print("\nActive Alerts:")
    for rule, count in alerts:
        print(f"  - {rule}: {count}")
else:
    print("\nNo active alerts")

# Check recent ISP alerts
cur.execute("""
    SELECT d.name, d.ip, a.rule_name, a.triggered_at
    FROM alert_history a
    JOIN standalone_devices d ON a.device_id = d.id
    WHERE d.ip LIKE '%.5'
    AND a.triggered_at > NOW() - INTERVAL '1 hour'
    ORDER BY a.triggered_at DESC
    LIMIT 5
""")
isp_alerts = cur.fetchall()
if isp_alerts:
    print("\nRecent ISP Link Alerts:")
    for name, ip, rule, time in isp_alerts:
        print(f"  - {name} ({ip}): {rule} at {time.strftime('%H:%M:%S')}")

cur.close()
conn.close()
EOF

# Monitor real-time alerts
echo ""
echo "📡 Monitoring real-time alert evaluation (10-second intervals)..."
echo ""

# Show Celery Beat schedule
docker exec wardops-beat-prod celery -A monitoring.celery_app inspect scheduled | grep -A3 "evaluate-alerts" || echo "Alert schedule not yet loaded"

# Check worker logs
echo ""
echo "🔍 Recent alert activity:"
docker logs wardops-worker-monitoring-prod --tail 50 2>&1 | grep -E "ISP|ALERT|FLAPPING|CRITICAL" || echo "No recent alert activity"

echo ""
echo "=========================================="
echo "✅ REAL-TIME ALERT SYSTEM DEPLOYED!"
echo "=========================================="
echo ""
echo "Alert Features Active:"
echo "  • 10-second detection for all devices"
echo "  • Priority monitoring for ISP links (.5 IPs)"
echo "  • Flapping suppression to prevent alert spam"
echo "  • Auto-resolution when devices recover"
echo ""
echo "Monitor alerts in real-time:"
echo "  docker logs -f wardops-worker-alerts-prod"
echo ""
echo "Check ISP link status:"
echo "  curl http://localhost:5001/api/v1/devices | jq '.[] | select(.ip | endswith(\".5\"))'"
echo ""
echo "View alert dashboard:"
echo "  http://10.30.25.46:5001/alerts"
echo ""