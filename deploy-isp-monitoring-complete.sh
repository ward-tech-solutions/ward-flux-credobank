#!/bin/bash
# ISP Monitoring - Complete Deployment Script
# Deploys interface polling, discovery, and UI updates
# Date: 2025-10-27

set -e  # Exit on error

echo "========================================"
echo "ISP MONITORING - COMPLETE DEPLOYMENT"
echo "========================================"
echo ""

# Check if running on correct server
if [ ! -d "/home/wardops/ward-flux-credobank" ]; then
    echo "ERROR: This script must run on production server (10.30.25.46)"
    exit 1
fi

cd /home/wardops/ward-flux-credobank

echo "Step 1: Pull latest code..."
git pull origin main
echo "✅ Code updated"
echo ""

echo "Step 2: Rebuild API container (includes React frontend)..."
docker compose -f docker-compose.production-priority-queues.yml stop api
docker compose -f docker-compose.production-priority-queues.yml rm -f api
docker compose -f docker-compose.production-priority-queues.yml build --no-cache api
docker compose -f docker-compose.production-priority-queues.yml up -d api
echo "✅ API container rebuilt"
echo ""

echo "Step 3: Rebuild SNMP worker (interface polling)..."
docker compose -f docker-compose.production-priority-queues.yml stop celery-worker-snmp
docker compose -f docker-compose.production-priority-queues.yml rm -f celery-worker-snmp
docker compose -f docker-compose.production-priority-queues.yml build --no-cache celery-worker-snmp
docker compose -f docker-compose.production-priority-queues.yml up -d celery-worker-snmp
echo "✅ SNMP worker rebuilt"
echo ""

echo "Step 4: Rebuild Celery Beat (scheduler)..."
docker compose -f docker-compose.production-priority-queues.yml stop celery-beat
docker compose -f docker-compose.production-priority-queues.yml rm -f celery-beat
docker compose -f docker-compose.production-priority-queues.yml build --no-cache celery-beat
docker compose -f docker-compose.production-priority-queues.yml up -d celery-beat
echo "✅ Celery Beat rebuilt"
echo ""

echo "Step 5: Wait for services to start..."
sleep 20
echo "✅ Services ready"
echo ""

echo "Step 6: Check container status..."
docker ps | grep -E "(api|worker-snmp|beat)" | grep -v "grep"
echo ""

echo "Step 7: Trigger initial interface discovery..."
echo "Discovering interfaces on all .5 routers..."
docker exec wardops-worker-snmp-prod python3 -c "
from celery import Celery
app = Celery('ward_flux')
app.config_from_object('celery_app_v2_priority_queues')
from monitoring.tasks_interface_discovery import discover_all_interfaces_task
result = discover_all_interfaces_task.delay()
print(f'Discovery task started: {result.id}')
"
echo "✅ Interface discovery triggered"
echo ""

echo "Step 8: Wait for discovery to complete (60 seconds)..."
sleep 60
echo ""

echo "Step 9: Verify deployment..."
echo ""
echo "Checking ISP interfaces in database..."
INTERFACE_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM device_interfaces WHERE interface_type = 'isp';")
echo "Total ISP interfaces: $INTERFACE_COUNT"
echo ""

if [ "$INTERFACE_COUNT" -gt 0 ]; then
    echo "✅ ISP interfaces discovered successfully!"
    echo ""
    echo "Sample ISP interfaces:"
    docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
    SELECT d.ip, di.if_name, di.if_alias, di.isp_provider, di.oper_status
    FROM device_interfaces di
    JOIN standalone_devices d ON di.device_id = d.id
    WHERE di.interface_type = 'isp'
    LIMIT 10;
    "
else
    echo "⚠️  WARNING: No ISP interfaces found. Check worker logs:"
    echo "docker logs wardops-worker-snmp-prod --tail 100"
fi
echo ""

echo "Step 10: Check scheduled tasks..."
echo "Recent Celery Beat schedule:"
docker logs wardops-celery-beat-prod --tail 30 | grep -E "(collect-interface|discover-all)" || echo "No recent logs yet (tasks may not have run)"
echo ""

echo "Step 11: Verify frontend is accessible..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5001 | grep -q "200"; then
    echo "✅ Frontend is accessible at http://10.30.25.46:5001"
else
    echo "⚠️  WARNING: Frontend not responding. Check API logs:"
    echo "docker logs wardops-api-prod --tail 50"
fi
echo ""

echo "========================================"
echo "DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "✅ What was deployed:"
echo "   - ISP interface discovery (daily at 2:30 AM)"
echo "   - ISP metrics collection (every 60 seconds)"
echo "   - Frontend: GREEN/RED ISP badges"
echo "   - Frontend: ISP status in DeviceDetails"
echo "   - Frontend: .5 router highlighting in Topology"
echo ""
echo "📊 Verification steps:"
echo "   1. Open http://10.30.25.46:5001/monitor"
echo "   2. Search for any .5 router (e.g., '57.5')"
echo "   3. Should see: SNMP (green), Magti (green/red), Silknet (green/red)"
echo "   4. Click device → DeviceDetails should show ISP Links"
echo "   5. Go to Topology → .5 routers show 🌍 icon"
echo ""
echo "🔍 Monitoring:"
echo "   - API logs: docker logs wardops-api-prod --tail 50 -f"
echo "   - SNMP worker: docker logs wardops-worker-snmp-prod --tail 50 -f"
echo "   - Celery Beat: docker logs wardops-celery-beat-prod --tail 50 -f"
echo ""
echo "📚 Documentation: ISP-MONITORING-COMPLETE.md"
echo ""
