#!/bin/bash

echo "🚨 CRITICAL PRODUCTION FIX - ALERT SYSTEM"
echo "=========================================="
echo ""
echo "This will fix the alert system to match Zabbix's 10-second detection"
echo ""

# SSH commands to run on production server
cat << 'REMOTE_SCRIPT' > /tmp/fix_production.sh
#!/bin/bash
cd /home/wardops/ward-flux-credobank

echo "Step 1: Pull latest code..."
git pull origin main

echo ""
echo "Step 2: Fix alert rules in database..."
docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops << 'SQL'
BEGIN;

-- Remove ALL existing alert rules
DELETE FROM alert_rules;

-- Insert correct alert rules
INSERT INTO alert_rules (id, name, description, expression, severity, enabled, device_id) VALUES
(gen_random_uuid(), 'Device Down', 'Device not responding to ping for 10+ seconds', 'down_time > 10 seconds', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'Device Flapping', 'Device experiencing intermittent connectivity', 'status_changes >= 3 in 5 minutes', 'HIGH', true, NULL),
(gen_random_uuid(), 'ISP Link Down', 'Internet service provider link is down', 'isp_link AND down_time > 10 seconds', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'ISP Link Flapping', 'ISP link experiencing intermittent connectivity', 'isp_link AND status_changes >= 2 in 5 minutes', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'ISP Link High Latency', 'ISP link latency exceeds threshold', 'isp_link AND response_time > 100ms', 'HIGH', true, NULL),
(gen_random_uuid(), 'ISP Link Packet Loss', 'ISP link experiencing packet loss', 'isp_link AND packet_loss > 5%', 'CRITICAL', true, NULL),
(gen_random_uuid(), 'High Latency', 'Response time exceeds threshold', 'response_time > 200ms', 'MEDIUM', true, NULL),
(gen_random_uuid(), 'Packet Loss Detected', 'Device experiencing packet loss', 'packet_loss > 10%', 'MEDIUM', true, NULL);

COMMIT;

SELECT name, severity FROM alert_rules ORDER BY severity, name;
SQL

echo ""
echo "Step 3: Create alerts for all DOWN devices..."
docker exec wardops-worker-monitoring-prod python3 create_alerts_now.py || \
docker exec wardops-worker-monitoring-prod python3 << 'PYTHON'
import psycopg2
from datetime import datetime
import uuid
import os

conn = psycopg2.connect(
    host='wardops-postgres-prod',
    database='ward_ops',
    user='ward_admin',
    password='SecureWardAdmin2024'
)

cur = conn.cursor()

# Get DOWN devices
cur.execute("""
    SELECT d.id, d.name, d.ip, d.down_since, d.branch_id, b.name
    FROM devices d
    LEFT JOIN branches b ON d.branch_id = b.id
    WHERE d.down_since IS NOT NULL
""")
down_devices = cur.fetchall()

# Get alert rules
cur.execute("SELECT id, name, severity FROM alert_rules WHERE enabled = true")
rules = {name: (id, severity) for id, name, severity in cur.fetchall()}

created = 0
for device_id, name, ip, down_since, branch_id, branch_name in down_devices:
    is_isp = ip and ip.endswith('.5')
    rule_name = 'ISP Link Down' if is_isp and 'ISP Link Down' in rules else 'Device Down'
    rule_id, severity = rules[rule_name]

    # Check existing
    cur.execute("SELECT 1 FROM alert_history WHERE device_id = %s AND rule_name = %s AND resolved_at IS NULL", (device_id, rule_name))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO alert_history (id, rule_id, rule_name, device_id, device_name,
                branch_id, branch_name, severity, triggered_at, message, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
        """, (str(uuid.uuid4()), rule_id, rule_name, device_id, name, branch_id, branch_name,
              severity, down_since, f"{name} ({ip}) is DOWN"))
        created += 1
        print(f"Created {severity} alert for {name} ({ip})")

conn.commit()
print(f"\nCreated {created} alerts")

# Show summary
cur.execute("""
    SELECT severity, COUNT(*) FROM alert_history
    WHERE resolved_at IS NULL GROUP BY severity ORDER BY severity
""")
for severity, count in cur.fetchall():
    print(f"  {severity}: {count}")

cur.close()
conn.close()
PYTHON

echo ""
echo "Step 4: Restart alert workers with fixed code..."
docker-compose -f docker-compose.production-priority-queues.yml restart wardops-worker-alerts-prod wardops-worker-monitoring-prod wardops-celery-beat-prod

echo ""
echo "Step 5: Verify alerts are working..."
sleep 5
echo "Recent alert logs:"
docker logs --tail 20 wardops-worker-alerts-prod 2>&1 | grep -E "(alert|FIXED|📊)"

echo ""
echo "Step 6: Final alert summary..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT 'Active alerts: ' || COUNT(*) || ' (CRITICAL: ' ||
       SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) || ', HIGH: ' ||
       SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) || ', MEDIUM: ' ||
       SUM(CASE WHEN severity = 'MEDIUM' THEN 1 ELSE 0 END) || ')'
FROM alert_history WHERE resolved_at IS NULL;
"

echo ""
echo "✅ FIX COMPLETE - Check http://10.30.25.46:5001/monitor"
REMOTE_SCRIPT

echo "Running fix on production server..."
ssh wardops@10.30.25.46 'bash -s' < /tmp/fix_production.sh