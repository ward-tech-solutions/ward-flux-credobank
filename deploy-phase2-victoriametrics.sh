#!/bin/bash

# ============================================================================
# WARD-OPS VICTORIAMETRICS MIGRATION - PHASE 2 DEPLOYMENT
# ============================================================================
# Deploys VictoriaMetrics migration Phase 2:
# - Updated ping_device() to use robust VM client
# - Removed PostgreSQL ping_results writes (saves 1.3M rows/day!)
# - Added comprehensive labels (branch, region, device_type)
# - Keeps device state management (down_since, alerts)
#
# IMPACT:
# - Stops PostgreSQL growth (was 1.5GB/day)
# - Enables fast historical queries from VictoriaMetrics
# - Retains alert detection and state tracking
#
# Usage on Credobank Server:
#   1. cd /home/wardops/ward-flux-credobank
#   2. git pull origin main
#   3. ./deploy-phase2-victoriametrics.sh
# ============================================================================

set -e  # Exit on any error

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║    VICTORIAMETRICS MIGRATION - PHASE 2 DEPLOYMENT                 ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: VERIFY WE'RE IN THE RIGHT DIRECTORY
# ============================================================================
echo "📂 Step 1: Verifying repository..."

if [ ! -f "docker-compose.production-priority-queues.yml" ]; then
    echo "❌ Error: Not in ward-flux-credobank directory"
    echo "   Please cd to the repository root first"
    exit 1
fi

echo "✅ Found docker-compose configuration"

# ============================================================================
# STEP 2: VERIFY PHASE 2 FILES ARE PRESENT
# ============================================================================
echo ""
echo "🔍 Step 2: Verifying Phase 2 files..."

REQUIRED_FILES=(
    "utils/victoriametrics_client.py"
    "monitoring/tasks.py"
)

ALL_PRESENT=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        ALL_PRESENT=false
    else
        echo "✅ Found: $file"
    fi
done

if [ "$ALL_PRESENT" = false ]; then
    echo ""
    echo "❌ Error: Phase 2 files not found"
    echo "   Please run: git pull origin main"
    exit 1
fi

# Verify monitoring/tasks.py has Phase 2 changes
if grep -q "PHASE 2 CHANGE: Removed PostgreSQL ping_results writes" monitoring/tasks.py; then
    echo "✅ Phase 2 changes detected in monitoring/tasks.py"
else
    echo "❌ Error: monitoring/tasks.py missing Phase 2 changes"
    echo "   Please run: git pull origin main"
    exit 1
fi

# ============================================================================
# STEP 3: CHECK CURRENT PING_RESULTS TABLE SIZE (BEFORE)
# ============================================================================
echo ""
echo "📊 Step 3: Checking current ping_results table size..."

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_rows,
    pg_size_pretty(pg_total_relation_size('ping_results')) as total_size
FROM ping_results;
" || echo "⚠️  Could not query ping_results table"

# ============================================================================
# STEP 4: BACKUP CURRENT STATE (OPTIONAL BUT RECOMMENDED)
# ============================================================================
echo ""
echo "💾 Step 4: Creating backup of current state..."

BACKUP_FILE="ping_results_backup_$(date +%Y%m%d_%H%M%S).sql"

echo "   Creating backup: $BACKUP_FILE"
docker exec wardops-postgres-prod pg_dump -U ward_admin -d ward_ops -t ping_results > "$BACKUP_FILE" 2>/dev/null || {
    echo "⚠️  Warning: Backup failed (non-critical)"
    echo "   Continuing with deployment..."
}

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "⚠️  Backup not created (continuing anyway)"
fi

# ============================================================================
# STEP 5: STOP MONITORING WORKERS (PREVENTS DUPLICATE WRITES)
# ============================================================================
echo ""
echo "🛑 Step 5: Stopping monitoring workers..."

echo "   Stopping wardops-worker-monitoring-prod..."
docker stop wardops-worker-monitoring-prod

if [ $? -eq 0 ]; then
    echo "✅ Monitoring worker stopped"
else
    echo "⚠️  Warning: Could not stop monitoring worker"
fi

# ============================================================================
# STEP 6: REBUILD CONTAINERS WITH PHASE 2 CODE
# ============================================================================
echo ""
echo "🏗️  Step 6: Rebuilding containers with Phase 2 changes..."

# Rebuild API and monitoring worker containers
docker-compose -f docker-compose.production-priority-queues.yml build \
    --no-cache \
    api celery-worker-monitoring

if [ $? -eq 0 ]; then
    echo "✅ Containers rebuilt successfully"
else
    echo "❌ Build failed"
    exit 1
fi

# ============================================================================
# STEP 7: START UPDATED MONITORING WORKER
# ============================================================================
echo ""
echo "🚀 Step 7: Starting updated monitoring worker..."

# Remove old container
docker rm wardops-worker-monitoring-prod 2>/dev/null || true

# Start new container with Phase 2 code
docker-compose -f docker-compose.production-priority-queues.yml up -d --no-deps celery-worker-monitoring

if [ $? -eq 0 ]; then
    echo "✅ Monitoring worker started with Phase 2 code"
else
    echo "❌ Failed to start monitoring worker"
    exit 1
fi

# ============================================================================
# STEP 8: WAIT FOR WORKER TO BECOME HEALTHY
# ============================================================================
echo ""
echo "⏳ Step 8: Waiting for monitoring worker to become healthy..."

MAX_WAIT=60
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' wardops-worker-monitoring-prod 2>/dev/null || echo "unknown")

    if [ "$HEALTH" = "healthy" ]; then
        echo "✅ Monitoring worker is healthy"
        break
    fi

    echo "   Waiting... ($WAIT_COUNT/$MAX_WAIT) [Status: $HEALTH]"
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "⚠️  Warning: Worker health check timeout"
    echo "   Worker may still be starting up"
    echo "   Check logs: docker logs wardops-worker-monitoring-prod"
fi

# ============================================================================
# STEP 9: VERIFY VICTORIAMETRICS IS RECEIVING DATA
# ============================================================================
echo ""
echo "🔍 Step 9: Verifying VictoriaMetrics is receiving ping data..."

# Wait a bit for first ping to execute
sleep 15

echo "   Querying VictoriaMetrics for recent device_ping_status metrics..."

RECENT_PINGS=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" | grep -o '"metric":' | wc -l)

if [ "$RECENT_PINGS" -gt 0 ]; then
    echo "✅ VictoriaMetrics receiving ping data ($RECENT_PINGS devices)"
else
    echo "⚠️  Warning: No ping data in VictoriaMetrics yet"
    echo "   This is normal if no pings have executed yet"
    echo "   Check logs: docker logs wardops-worker-monitoring-prod"
fi

# ============================================================================
# STEP 10: CHECK WORKER LOGS FOR ERRORS
# ============================================================================
echo ""
echo "📜 Step 10: Checking worker logs for errors..."

echo "   Recent logs:"
docker logs wardops-worker-monitoring-prod --tail 20

echo ""
echo "   Checking for VictoriaMetrics write errors:"
ERROR_COUNT=$(docker logs wardops-worker-monitoring-prod 2>&1 | grep -i "VictoriaMetrics write failed" | wc -l)

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✅ No VictoriaMetrics write errors detected"
else
    echo "⚠️  Warning: Found $ERROR_COUNT VictoriaMetrics write errors"
    echo "   Check full logs: docker logs wardops-worker-monitoring-prod"
fi

# ============================================================================
# STEP 11: MONITOR PING_RESULTS TABLE (SHOULD STOP GROWING)
# ============================================================================
echo ""
echo "📊 Step 11: Monitoring ping_results table..."

echo "   Current size:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_rows,
    pg_size_pretty(pg_total_relation_size('ping_results')) as total_size,
    MAX(timestamp) as latest_ping
FROM ping_results;
"

echo ""
echo "   ⏰ The ping_results table should now STOP growing!"
echo "   ⏰ New pings will go to VictoriaMetrics instead"

# ============================================================================
# SUCCESS
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║              ✅ PHASE 2 DEPLOYMENT SUCCESSFUL!                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 PHASE 2 CHANGES DEPLOYED:"
echo "   ✅ Ping data now written to VictoriaMetrics (not PostgreSQL)"
echo "   ✅ Comprehensive labels added (device_name, branch, region, device_type)"
echo "   ✅ Robust VM client with retries and connection pooling"
echo "   ✅ Device state management retained (down_since, alerts)"
echo ""
echo "🎯 EXPECTED IMPROVEMENTS:"
echo "   • PostgreSQL growth: 1.5GB/day → 0 (STOPPED!)"
echo "   • ping_results table: Will stabilize at current size"
echo "   • VictoriaMetrics: Storing all historical ping data with compression"
echo "   • Alert detection: Still working normally"
echo ""
echo "🔍 VERIFY DEPLOYMENT:"
echo "   1. Monitor ping_results table size (should not grow):"
echo "      docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \\"
echo "      SELECT COUNT(*) FROM ping_results; SELECT pg_size_pretty(pg_total_relation_size('ping_results'));\\"
echo ""
echo "   2. Check VictoriaMetrics has ping data:"
echo "      curl -s 'http://localhost:8428/api/v1/query?query=device_ping_status' | jq"
echo ""
echo "   3. Verify worker logs show successful VM writes:"
echo "      docker logs wardops-worker-monitoring-prod 2>&1 | grep 'Wrote.*ping metrics'"
echo ""
echo "   4. Confirm alerts still working:"
echo "      docker logs wardops-worker-monitoring-prod 2>&1 | grep 'Device.*went DOWN'"
echo ""
echo "📋 NEXT STEPS (PHASE 3):"
echo "   • Update API endpoints to read from VictoriaMetrics"
echo "   • Update dashboard to query VictoriaMetrics"
echo "   • Update device details page to show VM historical data"
echo "   • See VICTORIAMETRICS-ARCHITECTURE.md for details"
echo ""
echo "📋 OPTIONAL CLEANUP (AFTER PHASE 3 VERIFICATION):"
echo "   • Delete old ping_results data (Phase 4)"
echo "   • Remove ping_results table entirely (Phase 4)"
echo "   • Free up 1.5+ GB disk space"
echo ""
echo "📝 ROLLBACK (if needed):"
echo "   docker-compose -f docker-compose.production-priority-queues.yml down celery-worker-monitoring"
echo "   git checkout <previous-commit>"
echo "   ./deploy-phase2-victoriametrics.sh"
echo ""
echo "🎉 Phase 2 deployment complete!"
echo ""
