#!/usr/bin/env python3
"""
Create alerts for all currently DOWN devices in production
Uses device.down_since as source of truth
"""

import psycopg2
from datetime import datetime
import uuid

# Production database connection
conn = psycopg2.connect(
    host="10.30.25.46",
    port=5432,
    database="ward_ops",
    user="ward_admin",
    password="SecureWardAdmin2024"
)

cur = conn.cursor()

# Get all currently DOWN devices (down_since is NOT NULL)
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

if down_devices:
    print("\nDOWN devices:")
    for device in down_devices:
        device_id, device_name, device_ip, down_since, branch_id, branch_name = device
        print(f"  - {device_name} ({device_ip}) at {branch_name} - Down since: {down_since}")

# Get alert rules
cur.execute("""
    SELECT id, name, severity
    FROM alert_rules
    WHERE enabled = true
    ORDER BY name
""")
alert_rules = cur.fetchall()
print(f"\nFound {len(alert_rules)} enabled alert rules")

# Check which rules we need
device_down_rule = None
isp_down_rule = None

for rule_id, rule_name, severity in alert_rules:
    print(f"  - {rule_name} ({severity})")
    if rule_name == 'Device Down':
        device_down_rule = (rule_id, rule_name, severity)
    elif rule_name == 'ISP Link Down':
        isp_down_rule = (rule_id, rule_name, severity)

if not device_down_rule:
    print("\n❌ ERROR: 'Device Down' alert rule not found!")
    exit(1)

# Create alerts for each DOWN device
alerts_created = 0
for device in down_devices:
    device_id, device_name, device_ip, down_since, branch_id, branch_name = device

    # Determine which rule to use
    is_isp = device_ip and device_ip.endswith('.5')

    if is_isp and isp_down_rule:
        rule_id, rule_name, severity = isp_down_rule
        print(f"\nCreating ISP Link Down alert for {device_name} ({device_ip})")
    else:
        rule_id, rule_name, severity = device_down_rule
        print(f"\nCreating Device Down alert for {device_name} ({device_ip})")

    # Check if alert already exists
    cur.execute("""
        SELECT id FROM alert_history
        WHERE device_id = %s
        AND rule_name = %s
        AND resolved_at IS NULL
    """, (device_id, rule_name))

    existing_alert = cur.fetchone()

    if existing_alert:
        print(f"  ⚠️  Alert already exists for {device_name}")
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
                %s, %s, %s, %s,
                %s, NULL
            )
        """, (
            alert_id,
            rule_id,
            rule_name,
            device_id,
            device_name,
            branch_id,
            branch_name,
            severity,
            down_since,  # Use down_since as triggered_at
            f"{device_name} is DOWN - Not responding to ping"
        ))

        alerts_created += 1
        print(f"  ✅ Created {severity} alert for {device_name}")

# Commit the changes
conn.commit()

# Show summary
cur.execute("""
    SELECT
        COUNT(*) as total_alerts,
        COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_alerts,
        COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_alerts,
        COUNT(CASE WHEN severity = 'MEDIUM' THEN 1 END) as medium_alerts
    FROM alert_history
    WHERE resolved_at IS NULL
""")

summary = cur.fetchone()
print(f"\n📊 Alert Summary:")
print(f"  Total active alerts: {summary[0]}")
print(f"  - CRITICAL: {summary[1]}")
print(f"  - HIGH: {summary[2]}")
print(f"  - MEDIUM: {summary[3]}")
print(f"\n✅ Created {alerts_created} new alerts")

cur.close()
conn.close()