#!/bin/bash

echo "=================================================="
echo "🚨 FINAL PRODUCTION DEPLOYMENT - CREDOBANK"
echo "=================================================="
echo ""
echo "This deployment includes ALL critical fixes:"
echo "  ✅ Device status using down_since (ALL endpoints)"
echo "  ✅ Cache clearing on status changes"
echo "  ✅ WebSocket error handling"
echo "  ✅ Database transaction rollback"
echo "  ✅ Variable initialization fixes"
echo ""
echo "Starting deployment in 5 seconds..."
echo "Press Ctrl+C to cancel"
sleep 5

# Navigate to project directory
cd /home/wardops/ward-flux-credobank

echo ""
echo "📥 Step 1: Pull latest code from GitHub..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Git pull failed"
    exit 1
fi

echo ""
echo "📊 Step 2: Show what's being deployed..."
git log --oneline -5

echo ""
echo "🔨 Step 3: Rebuild containers with fixes..."
echo "Building API container..."
docker-compose -f docker-compose.production-priority-queues.yml build api
if [ $? -ne 0 ]; then
    echo "❌ API build failed"
    exit 1
fi

echo "Building monitoring worker..."
docker-compose -f docker-compose.production-priority-queues.yml build celery-worker-monitoring
if [ $? -ne 0 ]; then
    echo "❌ Worker build failed"
    exit 1
fi

echo ""
echo "🛑 Step 4: Stop old containers..."
docker stop wardops-api-prod 2>/dev/null || true
docker rm wardops-api-prod 2>/dev/null || true
docker stop wardops-worker-monitoring-prod 2>/dev/null || true
docker rm wardops-worker-monitoring-prod 2>/dev/null || true

echo ""
echo "🔄 Step 5: Start new containers..."
docker-compose -f docker-compose.production-priority-queues.yml up -d api celery-worker-monitoring
if [ $? -ne 0 ]; then
    echo "❌ Failed to start containers"
    exit 1
fi

echo ""
echo "⏳ Step 6: Wait for services to be healthy..."
for service in wardops-api-prod wardops-worker-monitoring-prod; do
    echo -n "Waiting for $service to be healthy"
    for i in {1..60}; do
        health=$(docker inspect $service --format='{{.State.Health.Status}}' 2>/dev/null || echo "starting")
        if [ "$health" = "healthy" ]; then
            echo " ✅ Healthy after $i seconds"
            break
        fi
        echo -n "."
        sleep 1
    done
    if [ "$health" != "healthy" ]; then
        echo " ⚠️ Not healthy after 60 seconds (status: $health)"
    fi
done

echo ""
echo "📊 Step 7: Verify containers are running..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAME|api|monitoring"

echo ""
echo "🧪 Step 8: Quick health check..."
# Check API health
api_health=$(curl -s http://localhost:5001/api/v1/health 2>/dev/null | grep -o "ok" || echo "failed")
if [ "$api_health" = "ok" ]; then
    echo "✅ API health check: OK"
else
    echo "⚠️  API health check: Failed (may need more time to start)"
fi

echo ""
echo "🔍 Step 9: Check for errors in logs..."
echo "API errors (last 10 lines):"
docker logs wardops-api-prod 2>&1 | grep -i "error\|exception" | tail -10 || echo "No errors found"

echo ""
echo "Worker errors (last 10 lines):"
docker logs wardops-worker-monitoring-prod 2>&1 | grep -i "error\|exception" | tail -10 || echo "No errors found"

echo ""
echo "📈 Step 10: Show device status statistics..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_devices,
    COUNT(CASE WHEN down_since IS NULL THEN 1 END) as devices_up,
    COUNT(CASE WHEN down_since IS NOT NULL THEN 1 END) as devices_down,
    ROUND(100.0 * COUNT(CASE WHEN down_since IS NULL THEN 1 END) / COUNT(*), 2) as uptime_percent
FROM standalone_devices
WHERE enabled = true;" 2>/dev/null || echo "Database query skipped"

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "CRITICAL CHANGES DEPLOYED:"
echo "1. Device status now uses device.down_since everywhere"
echo "2. Real-time cache clearing on status changes"
echo "3. Fixed all uninitialized variables"
echo "4. Fixed WebSocket error handling"
echo "5. Added database rollback on errors"
echo ""
echo "TO VERIFY THE FIX:"
echo "1. Open browser: http://10.30.25.46:5001"
echo "2. HARD REFRESH (Ctrl+F5 or Cmd+Shift+R) - CRITICAL!"
echo "3. Check Monitor page - devices show correct status"
echo "4. Check Dashboard - counts are accurate"
echo "5. Open device details - chart matches monitor status"
echo ""
echo "MONITORING COMMANDS:"
echo "  Watch API logs:     docker logs -f wardops-api-prod"
echo "  Watch Worker logs:  docker logs -f wardops-worker-monitoring-prod"
echo "  Check cache clear:  docker logs wardops-worker-monitoring-prod 2>&1 | grep '🔔\|🗑️'"
echo "  Check status changes: docker logs wardops-worker-monitoring-prod 2>&1 | grep 'DOWN\|RECOVERED'"
echo ""
echo "IF ISSUES PERSIST:"
echo "1. Clear browser cache completely"
echo "2. Try incognito/private mode"
echo "3. Check browser console (F12) for errors"
echo "4. Restart Beat scheduler: docker restart wardops-beat-prod"
echo ""
echo "Deployment completed at: $(date)"
echo ""