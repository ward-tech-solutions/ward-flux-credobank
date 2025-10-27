#!/bin/bash

echo "🚨 CREATING ALERTS FOR ALL DOWN DEVICES"
echo "======================================="
echo ""

# First, show current DOWN devices
echo "📊 Checking DOWN devices in database..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    d.name,
    d.ip,
    CASE WHEN d.ip LIKE '%.5' THEN 'ISP LINK' ELSE 'DEVICE' END as type,
    d.down_since,
    EXTRACT(EPOCH FROM (NOW() - d.down_since))::INT as seconds_down
FROM devices d
WHERE d.down_since IS NOT NULL
ORDER BY d.down_since;
"

echo ""
echo "📋 Current alert rules:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, severity, enabled FROM alert_rules ORDER BY severity, name;
"

echo ""
echo "🔧 Creating alerts using Python script..."

# Run the Python script inside the monitoring worker container
docker exec wardops-worker-monitoring-prod python3 << 'EOF'
import psycopg2
from datetime import datetime
import uuid
import os

# Database connection from environment
conn = psycopg2.connect(
    host=os.environ.get('POSTGRES_HOST', 'wardops-postgres-prod'),
    port=5432,
    database=os.environ.get('POSTGRES_DB', 'ward_ops'),
    user=os.environ.get('POSTGRES_USER', 'ward_admin'),
    password=os.environ.get('POSTGRES_PASSWORD', 'SecureWardAdmin2024')
)

cur = conn.cursor()

# Get all currently DOWN devices
cur.execute("""
    SELECT
        d.id,
        d.name,
        d.ip,
        d.down_since,
        d.branch_id,
        b.name as branch_name
    FROM devices d
    LEFT JOIN branches b ON d.branch_id = b.id
    WHERE d.down_since IS NOT NULL
    ORDER BY d.down_since
""")

down_devices = cur.fetchall()
print(f"Found {len(down_devices)} devices that are currently DOWN")

# Get alert rules
cur.execute("""
    SELECT id, name, severity
    FROM alert_rules
    WHERE enabled = true
    AND name IN ('Device Down', 'ISP Link Down')
""")
alert_rules = {name: (rule_id, severity) for rule_id, name, severity in cur.fetchall()}

if 'Device Down' not in alert_rules:
    print("ERROR: 'Device Down' rule not found!")
    exit(1)

alerts_created = 0
alerts_skipped = 0

for device_id, device_name, device_ip, down_since, branch_id, branch_name in down_devices:
    # Determine which rule to use
    is_isp = device_ip and device_ip.endswith('.5')

    if is_isp and 'ISP Link Down' in alert_rules:
        rule_name = 'ISP Link Down'
        rule_id, severity = alert_rules[rule_name]
        message = f"ISP Link {device_name} ({device_ip}) is DOWN"
    else:
        rule_name = 'Device Down'
        rule_id, severity = alert_rules[rule_name]
        message = f"{device_name} ({device_ip}) is DOWN - Not responding to ping"

    # Check if alert already exists
    cur.execute("""
        SELECT id FROM alert_history
        WHERE device_id = %s
        AND rule_name = %s
        AND resolved_at IS NULL
    """, (device_id, rule_name))

    if cur.fetchone():
        alerts_skipped += 1
        print(f"  ⏭️  Alert exists for {device_name}")
    else:
        # Create new alert
        alert_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO alert_history (
                id, rule_id, rule_name, device_id, device_name,
                branch_id, branch_name, severity, triggered_at,
                message, resolved_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, NULL
            )
        """, (
            alert_id, rule_id, rule_name, device_id, device_name,
            branch_id, branch_name, severity, down_since, message
        ))
        alerts_created += 1
        print(f"  ✅ Created {severity} alert: {message}")

conn.commit()

# Show final summary
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical,
        COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high,
        COUNT(CASE WHEN severity = 'MEDIUM' THEN 1 END) as medium
    FROM alert_history
    WHERE resolved_at IS NULL
""")

total, critical, high, medium = cur.fetchone()
print(f"\n📊 Alert Summary:")
print(f"  Total active alerts: {total}")
print(f"  - CRITICAL: {critical}")
print(f"  - HIGH: {high}")
print(f"  - MEDIUM: {medium}")
print(f"\n✅ Created {alerts_created} new alerts, skipped {alerts_skipped} existing")

cur.close()
conn.close()
EOF

echo ""
echo "✅ Alert creation complete!"
echo ""
echo "📊 Final database state:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    ah.severity,
    ah.rule_name,
    COUNT(*) as count,
    MIN(ah.triggered_at) as oldest_alert
FROM alert_history ah
WHERE ah.resolved_at IS NULL
GROUP BY ah.severity, ah.rule_name
ORDER BY
    CASE ah.severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        ELSE 4
    END,
    ah.rule_name;
"