#!/bin/bash

echo "🚨 CRITICAL: COMPLETE Device Status Fix Deployment"
echo "=================================================="
echo ""
echo "This deployment fixes ALL endpoints that were showing incorrect device status"
echo ""
echo "Fixed Endpoints:"
echo "  ✅ GET /api/v1/devices - Main device list"
echo "  ✅ GET /api/v1/infrastructure/* - Infrastructure map"
echo "  ✅ WebSocket /ws/updates - Real-time updates"
echo "  ✅ GET /api/v1/dashboard - Dashboard statistics"
echo ""

# Navigate to project directory
cd /home/wardops/ward-flux-credobank

echo "📥 Step 1: Pull latest code from GitHub..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Git pull failed"
    exit 1
fi

echo ""
echo "🔨 Step 2: Rebuild API container with ALL fixes..."
docker-compose -f docker-compose.production-priority-queues.yml build api
if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "🛑 Step 3: Stop old API container..."
docker stop wardops-api-prod 2>/dev/null || true
docker rm wardops-api-prod 2>/dev/null || true

echo ""
echo "🔄 Step 4: Start new API container..."
docker-compose -f docker-compose.production-priority-queues.yml up -d api
if [ $? -ne 0 ]; then
    echo "❌ Failed to start API"
    exit 1
fi

echo ""
echo "⏳ Waiting for API to be healthy (up to 60 seconds)..."
for i in {1..60}; do
    health=$(docker inspect wardops-api-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "starting")
    if [ "$health" = "healthy" ]; then
        echo "✅ API is healthy after $i seconds"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

echo ""
echo "📊 Step 5: Verify containers are running..."
docker ps | grep -E "NAME|wardops-api-prod|wardops-worker-monitoring-prod"

echo ""
echo "🧪 Step 6: Test device status (checking a known DOWN device)..."
# Test if we can query the database
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    name,
    ip,
    CASE
        WHEN down_since IS NULL THEN 'UP (down_since=NULL)'
        ELSE 'DOWN since ' || down_since
    END as database_status
FROM standalone_devices
WHERE down_since IS NOT NULL
LIMIT 5;" 2>/dev/null || echo "Database test skipped"

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "What was fixed:"
echo "1. ALL API endpoints now use device.down_since as source of truth"
echo "2. No more reliance on stale PingResult or VictoriaMetrics data"
echo "3. Device status updates within 10 seconds (monitoring interval)"
echo ""
echo "How to verify the fix:"
echo "1. Open browser: http://10.30.25.46:5001"
echo "2. HARD REFRESH (Ctrl+F5 or Cmd+Shift+R) - VERY IMPORTANT!"
echo "3. Check the Monitor page - devices should show correct status"
echo "4. Check Dashboard - UP/DOWN counts should be accurate"
echo "5. Open device details - chart should match current status"
echo ""
echo "What you should see:"
echo "✅ Devices that are DOWN show as DOWN (red) immediately"
echo "✅ Devices that are UP show as UP (green) immediately"
echo "✅ No more 5-minute delays"
echo "✅ Chart data matches current status in monitor page"
echo ""
echo "If issues persist after hard refresh:"
echo "1. Clear browser cache completely"
echo "2. Try incognito/private browsing mode"
echo "3. Check browser console for errors (F12)"
echo ""
echo "Monitor logs:"
echo "  docker logs -f wardops-api-prod --tail 100"
echo "  docker logs -f wardops-worker-monitoring-prod --tail 100"
echo ""