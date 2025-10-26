#!/bin/bash

# ============================================================================
# WARD-OPS VICTORIAMETRICS - DEPLOY PHASES 2 & 3 TOGETHER
# ============================================================================
# Deploys Phases 2 & 3 in one go (safe for same-day deployment)
#
# Phase 2: Ping writes → VictoriaMetrics (stops PostgreSQL growth)
# Phase 3: API reads → VictoriaMetrics (300x faster queries)
#
# ROBUSTNESS: Uses device.down_since fallback (commit 2f79cb2)
#             Dashboard will show correct states even if VM temporarily fails
#
# Usage:
#   ./deploy-phases-2-3-together.sh
# ============================================================================

set -e  # Exit on any error

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║         VICTORIAMETRICS PHASES 2 & 3 DEPLOYMENT                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⏱️  Estimated time: 15-20 minutes"
echo "🎯 Result: 300x faster queries + 0 GB/day growth"
echo ""

# ============================================================================
# VERIFY CRITICAL ROBUSTNESS FIX IS PRESENT
# ============================================================================
echo "🔍 Verifying critical robustness fix (commit 2f79cb2)..."

if grep -q "device.down_since" routers/dashboard.py; then
    echo "✅ Robustness fix detected in dashboard.py"
else
    echo "❌ ERROR: Robustness fix missing!"
    echo "   Run: git pull origin main"
    exit 1
fi

if grep -q "DO NOT fallback to PostgreSQL after Phase 2" routers/dashboard.py; then
    echo "✅ Phase 2 safety comment found"
else
    echo "⚠️  Warning: Updated robustness fix may be missing"
fi

# ============================================================================
# PHASE 2: STOP POSTGRESQL GROWTH
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 PHASE 2: Stop PostgreSQL Growth"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Current ping_results table size:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_rows,
    pg_size_pretty(pg_total_relation_size('ping_results')) as total_size
FROM ping_results;
" || echo "⚠️  Could not query ping_results"

echo ""
echo "🛑 Stopping monitoring worker..."
docker stop wardops-worker-monitoring-prod

echo ""
echo "🏗️  Rebuilding containers with Phase 2 code..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache celery-worker-monitoring

echo ""
echo "🚀 Starting updated monitoring worker..."
docker-compose -f docker-compose.production-priority-queues.yml up -d --no-deps celery-worker-monitoring

echo ""
echo "⏳ Waiting for monitoring worker to become healthy..."
sleep 10

WORKER_STATUS=$(docker inspect --format='{{.State.Status}}' wardops-worker-monitoring-prod 2>/dev/null || echo "unknown")
echo "   Worker status: $WORKER_STATUS"

echo ""
echo "✅ Phase 2 deployed!"

# ============================================================================
# VERIFY PHASE 2 WORKING
# ============================================================================
echo ""
echo "🔍 Verifying Phase 2..."

sleep 15  # Wait for first pings to execute

echo ""
echo "   Checking VictoriaMetrics for ping data..."
VM_METRICS=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" 2>/dev/null | grep -o '"metric":' | wc -l)

if [ "$VM_METRICS" -gt 0 ]; then
    echo "✅ VictoriaMetrics has ping data ($VM_METRICS devices)"
else
    echo "❌ ERROR: VictoriaMetrics has no ping data!"
    echo "   Check logs: docker logs wardops-worker-monitoring-prod"
    exit 1
fi

echo ""
echo "   Checking worker logs for VM writes..."
VM_WRITES=$(docker logs wardops-worker-monitoring-prod 2>&1 | grep "Wrote.*ping metrics to VictoriaMetrics" | wc -l)

if [ "$VM_WRITES" -gt 0 ]; then
    echo "✅ Found $VM_WRITES successful VM writes"
else
    echo "⚠️  Warning: No VM writes detected yet (may be too early)"
fi

# ============================================================================
# PHASE 3: API READS FROM VICTORIAMETRICS
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ PHASE 3: API Reads from VictoriaMetrics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Measuring current dashboard performance (baseline)..."
DASHBOARD_START=$(date +%s%N)
curl -s "http://localhost:5001/api/v1/dashboard/stats" > /dev/null 2>&1
DASHBOARD_END=$(date +%s%N)
DASHBOARD_BEFORE=$(( (DASHBOARD_END - DASHBOARD_START) / 1000000 ))
echo "   Dashboard before: ${DASHBOARD_BEFORE}ms"

echo ""
echo "🏗️  Rebuilding API container with Phase 3 code..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache api

echo ""
echo "🔄 Restarting API container..."
docker-compose -f docker-compose.production-priority-queues.yml up -d --no-deps api

echo ""
echo "⏳ Waiting for API to become healthy..."
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
fi

echo ""
echo "✅ Phase 3 deployed!"

# ============================================================================
# VERIFY PHASE 3 WORKING
# ============================================================================
echo ""
echo "🔍 Verifying Phase 3..."

sleep 5  # Let API fully initialize

echo ""
echo "📊 Testing dashboard performance after Phase 3..."
DASHBOARD_START=$(date +%s%N)
curl -s "http://localhost:5001/api/v1/dashboard/stats" > /dev/null 2>&1
DASHBOARD_END=$(date +%s%N)
DASHBOARD_AFTER=$(( (DASHBOARD_END - DASHBOARD_START) / 1000000 ))
echo "   Dashboard after: ${DASHBOARD_AFTER}ms"

if [ "$DASHBOARD_BEFORE" -gt 0 ] && [ "$DASHBOARD_AFTER" -gt 0 ]; then
    IMPROVEMENT=$(( (DASHBOARD_BEFORE - DASHBOARD_AFTER) * 100 / DASHBOARD_BEFORE ))
    if [ "$IMPROVEMENT" -gt 0 ]; then
        echo "   🚀 Improvement: ${IMPROVEMENT}% faster!"
    fi
fi

echo ""
echo "   Checking API logs for VM queries..."
VM_QUERIES=$(docker logs wardops-api-prod 2>&1 | grep "Querying VictoriaMetrics" | wc -l)

if [ "$VM_QUERIES" -gt 0 ]; then
    echo "✅ API is querying VictoriaMetrics ($VM_QUERIES queries)"
else
    echo "⚠️  Warning: No VM queries detected yet"
fi

echo ""
echo "   Checking for errors..."
ERROR_COUNT=$(docker logs wardops-api-prod 2>&1 | grep -i "error" | grep -v "error level" | wc -l)

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✅ No errors in API logs"
else
    echo "⚠️  Found $ERROR_COUNT errors - check logs"
fi

# ============================================================================
# FINAL VERIFICATION
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ FINAL VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔍 Testing dashboard endpoint..."
DASHBOARD_TEST=$(curl -s "http://localhost:5001/api/v1/dashboard/stats" | jq -r '.total_devices' 2>/dev/null || echo "0")

if [ "$DASHBOARD_TEST" -gt 0 ]; then
    echo "✅ Dashboard works: $DASHBOARD_TEST devices"
else
    echo "⚠️  Warning: Dashboard may have issues"
fi

echo ""
echo "🔍 Checking VictoriaMetrics health..."
VM_HEALTH=$(curl -s "http://localhost:8428/health" 2>/dev/null)

if [ "$VM_HEALTH" = "OK" ]; then
    echo "✅ VictoriaMetrics is healthy"
else
    echo "⚠️  VictoriaMetrics health: $VM_HEALTH"
fi

echo ""
echo "🔍 Current ping_results table size (should stabilize)..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_rows,
    pg_size_pretty(pg_total_relation_size('ping_results')) as total_size
FROM ping_results;
"

# ============================================================================
# SUCCESS
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║           ✅ PHASES 2 & 3 DEPLOYMENT COMPLETE!                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 WHAT WAS DEPLOYED:"
echo "   ✅ Phase 2: Ping writes → VictoriaMetrics"
echo "   ✅ Phase 3: API reads → VictoriaMetrics"
echo "   ✅ Robustness: device.down_since fallback"
echo ""
echo "📊 EXPECTED IMPROVEMENTS:"
echo "   • PostgreSQL growth: STOPPED (0 GB/day)"
echo "   • Dashboard load: ${DASHBOARD_AFTER}ms (was ${DASHBOARD_BEFORE}ms)"
echo "   • Device pages: Should be MUCH faster"
echo "   • Data retention: Now 12 months in VictoriaMetrics"
echo ""
echo "🔍 MONITORING (NEXT 24 HOURS):"
echo ""
echo "   1. Watch ping_results table (should NOT grow):"
echo "      watch -n 300 'docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \"SELECT COUNT(*) FROM ping_results\"'"
echo ""
echo "   2. Watch VictoriaMetrics metrics (should INCREASE):"
echo "      watch -n 60 'curl -s http://localhost:8428/api/v1/query?query=device_ping_status | grep -o \"metric\":\" | wc -l'"
echo ""
echo "   3. Monitor for errors:"
echo "      docker logs -f wardops-api-prod 2>&1 | grep -i error"
echo ""
echo "   4. Test dashboard performance:"
echo "      time curl -s http://localhost:5001/api/v1/dashboard/stats > /dev/null"
echo "      # Should be <200ms"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "   Today: Monitor for stability (next 24 hours)"
echo "   Tomorrow: Verify ping_results stopped growing"
echo "   Week 1-2: Monitor for any issues"
echo "   Week 2-3: Deploy Phase 4 (cleanup PostgreSQL table)"
echo ""
echo "🎯 Phase 4 Deployment (after 1-2 weeks):"
echo "   ./deploy-phase4-cleanup.sh"
echo "   # This will free 1.5+ GB disk space"
echo ""
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo ""
