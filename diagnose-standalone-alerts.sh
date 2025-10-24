#!/bin/bash

# ============================================================================
# WARD-OPS STANDALONE MONITORING DIAGNOSTIC
# ============================================================================
# Diagnoses why standalone ping monitoring is NOT catching device outages
# while Zabbix (competitor) IS catching them
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║       WARD-OPS STANDALONE MONITORING DIAGNOSTICS                  ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: CHECK MONITORING MODE
# ============================================================================
echo "🔍 Step 1: Verifying monitoring mode is STANDALONE..."
echo ""

docker exec wardops-api-prod env | grep MONITORING_MODE

# ============================================================================
# STEP 2: CHECK PING MONITORING WORKER
# ============================================================================
echo ""
echo "📡 Step 2: Checking ping monitoring worker..."
echo ""

WORKER_STATUS=$(docker inspect wardops-worker-monitoring-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "not found")
echo "Monitoring Worker Status: $WORKER_STATUS"

if [ "$WORKER_STATUS" != "healthy" ]; then
    echo "❌ Monitoring worker is $WORKER_STATUS - PINGS NOT WORKING!"
    echo ""
    echo "Recent logs:"
    docker logs wardops-worker-monitoring-prod --tail 50
else
    echo "✅ Monitoring worker is healthy"
fi

# ============================================================================
# STEP 3: CHECK LAGODEKHI DEVICES IN DATABASE
# ============================================================================
echo ""
echo "📱 Step 3: Checking Lagodekhi devices (mentioned in Zabbix alerts)..."
echo ""

echo "Looking for Lagodekhi-NVR (10.199.63.140):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    name,
    ip_address,
    enabled,
    down_since,
    last_ping_at,
    CASE
        WHEN down_since IS NOT NULL THEN 'DOWN'
        ELSE 'UP'
    END as status
FROM devices
WHERE ip_address = '10.199.63.140' OR name ILIKE '%Lagodekhi%NVR%'
LIMIT 5;
"

echo ""
echo "Looking for Lagodekhi-AP (10.195.63.252):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    name,
    ip_address,
    enabled,
    down_since,
    last_ping_at,
    CASE
        WHEN down_since IS NOT NULL THEN 'DOWN'
        ELSE 'UP'
    END as status
FROM devices
WHERE ip_address = '10.195.63.252' OR name ILIKE '%Lagodekhi%AP%'
LIMIT 5;
"

# ============================================================================
# STEP 4: CHECK RECENT PING RESULTS
# ============================================================================
echo ""
echo "🏓 Step 4: Checking recent ping results for these IPs..."
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    d.name,
    d.ip_address,
    pr.is_reachable,
    pr.response_time_ms,
    pr.created_at,
    pr.error_message
FROM ping_results pr
JOIN devices d ON pr.device_id = d.id
WHERE d.ip_address IN ('10.199.63.140', '10.195.63.252')
ORDER BY pr.created_at DESC
LIMIT 10;
"

# ============================================================================
# STEP 5: CHECK IF PING TASKS ARE RUNNING
# ============================================================================
echo ""
echo "⏱️  Step 5: Checking if ping tasks are scheduled..."
echo ""

docker exec wardops-beat-prod celery -A celery_app inspect scheduled 2>/dev/null | grep -A 3 "ping_devices" || echo "⚠️  No ping tasks scheduled!"

# ============================================================================
# STEP 6: CHECK ALERT RULES FOR DEVICE DOWN
# ============================================================================
echo ""
echo "📋 Step 6: Checking alert rules for device down events..."
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    id,
    name,
    enabled,
    severity,
    condition_type,
    condition_value,
    description
FROM alert_rules
WHERE enabled = true
  AND (condition_type = 'device_down' OR name ILIKE '%down%' OR name ILIKE '%ping%')
ORDER BY severity DESC;
"

# ============================================================================
# STEP 7: CHECK RECENT ALERTS
# ============================================================================
echo ""
echo "🔔 Step 7: Checking recent alerts in database..."
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_alerts,
    COUNT(*) FILTER (WHERE resolved_at IS NULL) as unresolved,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_hour,
    MAX(created_at) as most_recent_alert
FROM alerts;
"

echo ""
echo "Most recent 5 alerts:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    a.severity,
    a.message,
    d.name as device_name,
    d.ip_address,
    a.created_at,
    a.resolved_at
FROM alerts a
LEFT JOIN devices d ON a.device_id = d.id
ORDER BY a.created_at DESC
LIMIT 5;
"

# ============================================================================
# STEP 8: CHECK CELERY BEAT (SCHEDULER)
# ============================================================================
echo ""
echo "🔔 Step 8: Checking Celery Beat status..."
echo ""

BEAT_STATUS=$(docker inspect wardops-beat-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "not found")
echo "Celery Beat Status: $BEAT_STATUS"

if [ "$BEAT_STATUS" != "healthy" ]; then
    echo "❌ Celery Beat is $BEAT_STATUS - tasks not scheduled!"
    echo ""
    echo "Recent Beat logs:"
    docker logs wardops-beat-prod --tail 30
fi

# ============================================================================
# STEP 9: MANUALLY PING LAGODEKHI DEVICES
# ============================================================================
echo ""
echo "🧪 Step 9: Manually pinging Lagodekhi devices from container..."
echo ""

echo "Pinging 10.199.63.140 (Lagodekhi-NVR):"
docker exec wardops-worker-monitoring-prod ping -c 3 -W 1 10.199.63.140 2>&1 || echo "❌ Ping failed!"

echo ""
echo "Pinging 10.195.63.252 (Lagodekhi-AP):"
docker exec wardops-worker-monitoring-prod ping -c 3 -W 1 10.195.63.252 2>&1 || echo "❌ Ping failed!"

# ============================================================================
# STEP 10: CHECK MONITORING TASK LOGS
# ============================================================================
echo ""
echo "📜 Step 10: Checking monitoring worker logs for errors..."
echo ""

docker logs wardops-worker-monitoring-prod 2>&1 | grep -i "error\|exception\|failed\|lagodekhi" | tail -30

# ============================================================================
# STEP 11: CHECK ALERT WORKER LOGS
# ============================================================================
echo ""
echo "📜 Step 11: Checking alert worker logs..."
echo ""

docker logs wardops-worker-alerts-prod 2>&1 | grep -i "error\|exception\|failed\|evaluate" | tail -30

# ============================================================================
# STEP 12: TRIGGER MANUAL PING FOR LAGODEKHI DEVICES
# ============================================================================
echo ""
echo "🧪 Step 12: Triggering manual ping task..."
echo ""

docker exec wardops-api-prod python3 -c "
from celery_app import celery_app
from database import SessionLocal
from models import Device

db = SessionLocal()
try:
    # Find Lagodekhi devices
    devices = db.query(Device).filter(
        Device.ip_address.in_(['10.199.63.140', '10.195.63.252'])
    ).all()

    if devices:
        print(f'Found {len(devices)} Lagodekhi devices')
        for dev in devices:
            print(f'  - {dev.name} ({dev.ip_address})')

        # Trigger ping tasks
        result = celery_app.send_task('monitoring.tasks.ping_devices_batch')
        print(f'✅ Ping task triggered: {result.id}')
    else:
        print('❌ No Lagodekhi devices found in database!')
        print('   Searching for any device with these IPs...')
        all_devices = db.query(Device).filter(Device.ip_address.like('%199.63%')).all()
        for dev in all_devices:
            print(f'   Found: {dev.name} - {dev.ip_address}')
finally:
    db.close()
" 2>&1

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                      DIAGNOSTIC COMPLETE                           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "POSSIBLE ISSUES:"
echo "1. Devices not in Ward-Ops database (but in Zabbix)"
echo "2. Ping monitoring worker not running or failing"
echo "3. Alert rules not configured for device down events"
echo "4. Celery Beat not scheduling ping tasks"
echo "5. Network connectivity issue from container"
echo "6. Alert evaluation not triggering for down devices"
echo ""
echo "CHECK THE OUTPUT ABOVE TO IDENTIFY THE ROOT CAUSE"
echo ""
