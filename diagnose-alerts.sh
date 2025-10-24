#!/bin/bash

# ============================================================================
# WARD-OPS ALERT DETECTION DIAGNOSTIC SCRIPT
# ============================================================================
# Diagnoses why Zabbix alerts are not appearing in Ward-Ops
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          WARD-OPS ALERT DETECTION DIAGNOSTICS                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: CHECK ALERT WORKER STATUS
# ============================================================================
echo "📊 Step 1: Checking alert evaluation worker..."
echo ""

WORKER_STATUS=$(docker inspect wardops-worker-alerts-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "not found")
echo "Alert Worker Status: $WORKER_STATUS"

if [ "$WORKER_STATUS" != "healthy" ]; then
    echo "⚠️  Alert worker is $WORKER_STATUS"
    echo ""
    echo "Recent logs:"
    docker logs wardops-worker-alerts-prod --tail 30
else
    echo "✅ Alert worker is healthy"
fi

# ============================================================================
# STEP 2: CHECK ZABBIX INTEGRATION CONFIGURATION
# ============================================================================
echo ""
echo "📡 Step 2: Checking Zabbix integration..."
echo ""

docker exec wardops-api-prod python3 -c "
from database import SessionLocal
from models import Integration

db = SessionLocal()
try:
    zabbix = db.query(Integration).filter(Integration.type == 'zabbix').first()
    if zabbix:
        print(f'✅ Zabbix integration found: {zabbix.name}')
        print(f'   Enabled: {zabbix.enabled}')
        print(f'   URL: {zabbix.config.get(\"url\") if zabbix.config else \"Not set\"}')
        print(f'   Last sync: {zabbix.last_sync_at}')
    else:
        print('❌ No Zabbix integration configured')
finally:
    db.close()
" 2>&1

# ============================================================================
# STEP 3: CHECK RECENT ALERTS IN DATABASE
# ============================================================================
echo ""
echo "🔍 Step 3: Checking recent alerts in database..."
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_alerts,
    COUNT(*) FILTER (WHERE resolved_at IS NULL) as unresolved,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_hour,
    MAX(created_at) as most_recent_alert
FROM alerts;
"

# ============================================================================
# STEP 4: CHECK ALERT EVALUATION CELERY TASK
# ============================================================================
echo ""
echo "⏱️  Step 4: Checking alert evaluation task schedule..."
echo ""

docker exec wardops-beat-prod celery -A celery_app inspect scheduled 2>/dev/null | grep -A 5 "evaluate_alerts" || echo "No scheduled alert evaluation tasks found"

# ============================================================================
# STEP 5: CHECK CELERY BEAT STATUS
# ============================================================================
echo ""
echo "🔔 Step 5: Checking Celery Beat (task scheduler)..."
echo ""

BEAT_STATUS=$(docker inspect wardops-beat-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "not found")
echo "Celery Beat Status: $BEAT_STATUS"

if [ "$BEAT_STATUS" != "healthy" ]; then
    echo "⚠️  Celery Beat is $BEAT_STATUS - alerts won't be evaluated!"
    echo ""
    echo "Recent logs:"
    docker logs wardops-beat-prod --tail 30
fi

# ============================================================================
# STEP 6: CHECK RECENT DEVICE STATUS
# ============================================================================
echo ""
echo "📱 Step 6: Checking devices matching Zabbix alert IPs..."
echo ""

# Check for the specific devices mentioned in Zabbix alerts
echo "Checking Lagodekhi-NVR (10.199.63.140):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, ip_address, down_since, last_ping_at
FROM devices
WHERE ip_address = '10.199.63.140' OR name LIKE '%Lagodekhi%NVR%';
"

echo ""
echo "Checking Lagodekhi-AP (10.195.63.252):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT name, ip_address, down_since, last_ping_at
FROM devices
WHERE ip_address = '10.195.63.252' OR name LIKE '%Lagodekhi%AP%';
"

# ============================================================================
# STEP 7: CHECK ALERT RULES
# ============================================================================
echo ""
echo "📋 Step 7: Checking alert rules configuration..."
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    id,
    name,
    enabled,
    severity,
    condition_type,
    condition_value
FROM alert_rules
WHERE enabled = true
ORDER BY severity DESC;
"

# ============================================================================
# STEP 8: MANUAL ALERT EVALUATION TEST
# ============================================================================
echo ""
echo "🧪 Step 8: Triggering manual alert evaluation..."
echo ""

docker exec wardops-api-prod python3 -c "
from celery_app import celery_app

# Trigger alert evaluation manually
result = celery_app.send_task('monitoring.tasks.evaluate_alerts')
print(f'✅ Alert evaluation task triggered: {result.id}')
print('   Waiting 5 seconds for results...')

import time
time.sleep(5)

# Check task status
print(f'   Task state: {result.state}')
if result.state == 'SUCCESS':
    print(f'   Result: {result.result}')
elif result.state == 'FAILURE':
    print(f'   Error: {result.info}')
else:
    print(f'   Status: {result.state} (may still be processing)')
" 2>&1

# ============================================================================
# STEP 9: CHECK FOR RECENT ALERT EVALUATION ERRORS
# ============================================================================
echo ""
echo "❌ Step 9: Checking for alert evaluation errors..."
echo ""

echo "API logs (alert-related errors):"
docker logs wardops-api-prod 2>&1 | grep -i "alert\|error" | tail -20

echo ""
echo "Alert Worker logs (recent errors):"
docker logs wardops-worker-alerts-prod 2>&1 | grep -i "error\|exception\|failed" | tail -20

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                      DIAGNOSTIC COMPLETE                           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "NEXT STEPS:"
echo "1. Review the output above for any errors or misconfigurations"
echo "2. Check if Zabbix integration is enabled and configured correctly"
echo "3. Verify alert rules exist and are enabled"
echo "4. Ensure Celery Beat is healthy (schedules alert evaluations)"
echo "5. Check if devices exist in Ward-Ops database"
echo ""
