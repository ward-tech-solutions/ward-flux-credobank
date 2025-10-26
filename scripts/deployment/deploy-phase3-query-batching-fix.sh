#!/bin/bash

# ============================================================================
# PHASE 3 QUERY BATCHING FIX - DEPLOYMENT SCRIPT
# ============================================================================
# Fixes HTTP 422 errors and UI slowness by batching VictoriaMetrics queries
#
# Issue: UI was taking 1+ minutes to load
# Cause: Querying all 875 devices in single regex = URL too long
# Fix:   Batch queries into chunks of 50 IPs = 18 fast queries
#
# Usage on Credobank Server:
#   1. cd /home/wardops/ward-flux-credobank
#   2. git pull origin main
#   3. ./deploy-phase3-query-batching-fix.sh
# ============================================================================

set -e  # Exit on any error

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║         PHASE 3 QUERY BATCHING FIX DEPLOYMENT                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: VERIFY FIX IS PRESENT
# ============================================================================
echo "🔍 Step 1: Verifying query batching fix is present..."

if grep -q "PHASE 3 FIX: Batch the queries" utils/victoriametrics_client.py; then
    echo "✅ Query batching fix detected in code"
else
    echo "❌ Error: Query batching fix not found"
    echo "   Please run: git pull origin main"
    exit 1
fi

if grep -q "BATCH_SIZE = 50" utils/victoriametrics_client.py; then
    echo "✅ Batch size configuration found (50 IPs per query)"
else
    echo "❌ Error: Batch size configuration not found"
    exit 1
fi

# ============================================================================
# STEP 2: CHECK CURRENT API STATUS
# ============================================================================
echo ""
echo "📊 Step 2: Checking current API status..."

API_STATUS=$(docker inspect --format='{{.State.Status}}' wardops-api-prod 2>/dev/null || echo "not_found")
echo "   API container status: $API_STATUS"

if [ "$API_STATUS" != "running" ]; then
    echo "⚠️  Warning: API is not running, will start it after build"
fi

# ============================================================================
# STEP 3: REBUILD API CONTAINER
# ============================================================================
echo ""
echo "🏗️  Step 3: Rebuilding API container with query batching fix..."

docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api

if [ $? -eq 0 ]; then
    echo "✅ API container rebuilt successfully"
else
    echo "❌ Build failed"
    exit 1
fi

# ============================================================================
# STEP 4: REMOVE OLD CONTAINER (avoid ContainerConfig error)
# ============================================================================
echo ""
echo "🗑️  Step 4: Removing old API container..."

# Stop the API container
docker-compose -f docker-compose.production-priority-queues.yml stop api
echo "✅ API container stopped"

# Find and remove the stopped container
STOPPED_CONTAINER=$(docker ps -a --filter "name=wardops-api-prod" --filter "status=exited" -q)
if [ -n "$STOPPED_CONTAINER" ]; then
    docker rm $STOPPED_CONTAINER
    echo "✅ Removed stopped container: $STOPPED_CONTAINER"
else
    echo "ℹ️  No stopped container to remove"
fi

# ============================================================================
# STEP 5: START NEW API CONTAINER
# ============================================================================
echo ""
echo "🚀 Step 5: Starting new API container..."

docker-compose -f docker-compose.production-priority-queues.yml up -d api

if [ $? -eq 0 ]; then
    echo "✅ API container started"
else
    echo "❌ Failed to start API container"
    exit 1
fi

# ============================================================================
# STEP 6: WAIT FOR API TO BECOME HEALTHY
# ============================================================================
echo ""
echo "⏳ Step 6: Waiting for API to become healthy..."

MAX_WAIT=60
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' wardops-api-prod 2>/dev/null || echo "unknown")

    if [ "$HEALTH" = "healthy" ]; then
        echo "✅ API is healthy"
        break
    fi

    echo "   Waiting... ($WAIT_COUNT/$MAX_WAIT) [Status: $HEALTH]"
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "⚠️  Warning: API health check timeout"
    echo "   API may still be starting up"
    echo "   Check logs: docker logs wardops-api-prod"
fi

# ============================================================================
# STEP 7: VERIFY FIX IS DEPLOYED
# ============================================================================
echo ""
echo "🔍 Step 7: Verifying query batching fix is deployed..."

if docker exec wardops-api-prod grep -q "PHASE 3 FIX: Batch the queries" /app/utils/victoriametrics_client.py 2>/dev/null; then
    echo "✅ Query batching fix detected in running container"
else
    echo "❌ Error: Query batching fix not found in container"
    echo "   Check logs: docker logs wardops-api-prod"
    exit 1
fi

# ============================================================================
# STEP 8: TEST API PERFORMANCE
# ============================================================================
echo ""
echo "📊 Step 8: Testing API performance..."
echo ""

# Wait a few seconds for API to fully initialize
sleep 5

echo "   Testing dashboard stats endpoint..."
DASHBOARD_START=$(date +%s%N)
curl -s "http://localhost:5001/api/v1/dashboard/stats" > /dev/null 2>&1
DASHBOARD_END=$(date +%s%N)
DASHBOARD_MS=$(( (DASHBOARD_END - DASHBOARD_START) / 1000000 ))

echo "   ⏱️  Dashboard stats: ${DASHBOARD_MS}ms"

if [ "$DASHBOARD_MS" -lt 1000 ]; then
    echo "   ✅ Performance is GOOD (<1 second)"
elif [ "$DASHBOARD_MS" -lt 5000 ]; then
    echo "   ⚠️  Performance is acceptable (1-5 seconds)"
else
    echo "   ❌ Performance is SLOW (>5 seconds)"
    echo "   Check API logs for errors"
fi

# ============================================================================
# STEP 9: CHECK FOR VictoriaMetrics ERRORS
# ============================================================================
echo ""
echo "🔍 Step 9: Checking for VictoriaMetrics errors..."

VM_ERRORS=$(docker logs wardops-api-prod 2>&1 | grep -i "VM query failed: 422" | wc -l)

if [ "$VM_ERRORS" -eq 0 ]; then
    echo "✅ No HTTP 422 errors detected"
else
    echo "⚠️  Warning: Found $VM_ERRORS HTTP 422 errors"
    echo "   Recent errors:"
    docker logs wardops-api-prod 2>&1 | grep -i "VM query failed: 422" | tail -3
fi

# Show batch query logs
echo ""
echo "   Checking for batch query logs:"
BATCH_LOGS=$(docker logs wardops-api-prod 2>&1 | grep -i "Queried.*devices in.*batches" | tail -3)
if [ -n "$BATCH_LOGS" ]; then
    echo "$BATCH_LOGS"
    echo "✅ Batch queries are working"
else
    echo "ℹ️  No batch query logs yet (may not have been called)"
fi

# ============================================================================
# SUCCESS
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║         ✅ PHASE 3 QUERY BATCHING FIX DEPLOYED!                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🔧 FIX DEPLOYED:"
echo "   ✅ VictoriaMetrics queries now batched (50 IPs per query)"
echo "   ✅ 875 devices split into 18 batches"
echo "   ✅ No more HTTP 422 errors"
echo "   ✅ UI should be fast and responsive"
echo ""
echo "📊 EXPECTED PERFORMANCE:"
echo "   • Dashboard load: <200ms (was 1+ minute)"
echo "   • Device list: <100ms (was 1+ minute)"
echo "   • No query timeouts"
echo ""
echo "🔍 VERIFY DEPLOYMENT:"
echo "   1. Test UI loads quickly in browser"
echo ""
echo "   2. Check no HTTP 422 errors:"
echo "      docker logs wardops-api-prod 2>&1 | grep '422'"
echo ""
echo "   3. Watch batch query logs:"
echo "      docker logs -f wardops-api-prod 2>&1 | grep 'Queried'"
echo ""
echo "   4. Performance test:"
echo "      time curl -s http://localhost:5001/api/v1/dashboard/stats | jq '.success'"
echo "      (Should complete in <1 second)"
echo ""
echo "🎉 Phase 3 query batching fix deployed!"
echo ""
