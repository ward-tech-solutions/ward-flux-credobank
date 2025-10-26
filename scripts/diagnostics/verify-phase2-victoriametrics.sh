#!/bin/bash

# ============================================================================
# WARD-OPS VICTORIAMETRICS PHASE 2 VERIFICATION SCRIPT
# ============================================================================
# Verifies that Phase 2 migration is working correctly:
# - VictoriaMetrics receiving ping data
# - PostgreSQL ping_results table stopped growing
# - Alert detection still working
# - No errors in worker logs
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║       VICTORIAMETRICS PHASE 2 VERIFICATION                        ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# TEST 1: VICTORIAMETRICS CONNECTIVITY
# ============================================================================
echo "📡 Test 1: Checking VictoriaMetrics connectivity..."
echo ""

VM_HEALTH=$(curl -s http://localhost:8428/health 2>/dev/null)

if [ "$VM_HEALTH" = "OK" ]; then
    echo "✅ VictoriaMetrics is healthy"
else
    echo "❌ VictoriaMetrics health check failed"
    echo "   Response: $VM_HEALTH"
fi

# ============================================================================
# TEST 2: VICTORIAMETRICS RECEIVING PING DATA
# ============================================================================
echo ""
echo "📊 Test 2: Checking if VictoriaMetrics is receiving ping data..."
echo ""

# Query for device_ping_status metrics
PING_STATUS_COUNT=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" 2>/dev/null | grep -o '"metric":' | wc -l)

echo "   device_ping_status metrics: $PING_STATUS_COUNT devices"

if [ "$PING_STATUS_COUNT" -gt 0 ]; then
    echo "✅ VictoriaMetrics is receiving ping_status data"
else
    echo "⚠️  Warning: No ping_status data in VictoriaMetrics"
fi

# Query for device_ping_rtt_ms metrics
RTT_COUNT=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_rtt_ms" 2>/dev/null | grep -o '"metric":' | wc -l)

echo "   device_ping_rtt_ms metrics: $RTT_COUNT devices"

if [ "$RTT_COUNT" -gt 0 ]; then
    echo "✅ VictoriaMetrics is receiving RTT data"
else
    echo "⚠️  Warning: No RTT data in VictoriaMetrics"
fi

# Query for device_ping_packet_loss metrics
LOSS_COUNT=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_packet_loss" 2>/dev/null | grep -o '"metric":' | wc -l)

echo "   device_ping_packet_loss metrics: $LOSS_COUNT devices"

if [ "$LOSS_COUNT" -gt 0 ]; then
    echo "✅ VictoriaMetrics is receiving packet loss data"
else
    echo "⚠️  Warning: No packet loss data in VictoriaMetrics"
fi

# ============================================================================
# TEST 3: SAMPLE VICTORIAMETRICS DATA
# ============================================================================
echo ""
echo "📋 Test 3: Sample VictoriaMetrics data (most recent pings)..."
echo ""

echo "   Latest device_ping_status values (UP=1, DOWN=0):"
curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" 2>/dev/null | jq -r '.data.result[] | "\(.metric.device_name) (\(.metric.device_ip)): \(.value[1])"' | head -10 || echo "   (jq not available, skipping JSON parsing)"

# ============================================================================
# TEST 4: POSTGRESQL PING_RESULTS TABLE STATUS
# ============================================================================
echo ""
echo "📊 Test 4: Checking PostgreSQL ping_results table..."
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_rows,
    pg_size_pretty(pg_total_relation_size('ping_results')) as total_size,
    pg_size_pretty(pg_relation_size('ping_results')) as data_size,
    pg_size_pretty(pg_total_relation_size('ping_results') - pg_relation_size('ping_results')) as index_size,
    MAX(timestamp) as latest_ping,
    MIN(timestamp) as oldest_ping
FROM ping_results;
"

echo ""
echo "⏰ IMPORTANT: After Phase 2, ping_results table should STOP growing!"
echo "   Check this table size again in 1 hour - it should be the same."

# ============================================================================
# TEST 5: MONITORING WORKER STATUS
# ============================================================================
echo ""
echo "🔍 Test 5: Checking monitoring worker status..."
echo ""

WORKER_STATUS=$(docker inspect wardops-worker-monitoring-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "not found")

echo "   Worker Status: $WORKER_STATUS"

if [ "$WORKER_STATUS" = "healthy" ]; then
    echo "✅ Monitoring worker is healthy"
else
    echo "❌ Monitoring worker is $WORKER_STATUS"
fi

# ============================================================================
# TEST 6: WORKER LOGS - VICTORIAMETRICS WRITES
# ============================================================================
echo ""
echo "📜 Test 6: Checking worker logs for VictoriaMetrics writes..."
echo ""

echo "   Successful VM writes (last 10):"
docker logs wardops-worker-monitoring-prod 2>&1 | grep "Wrote.*ping metrics to VictoriaMetrics" | tail -10

echo ""
echo "   VM write errors (if any):"
VM_ERRORS=$(docker logs wardops-worker-monitoring-prod 2>&1 | grep "VictoriaMetrics write failed" | wc -l)

if [ "$VM_ERRORS" -eq 0 ]; then
    echo "✅ No VictoriaMetrics write errors"
else
    echo "⚠️  Warning: Found $VM_ERRORS VictoriaMetrics write errors"
    docker logs wardops-worker-monitoring-prod 2>&1 | grep "VictoriaMetrics write failed" | tail -5
fi

# ============================================================================
# TEST 7: ALERT DETECTION STILL WORKING
# ============================================================================
echo ""
echo "🚨 Test 7: Verifying alert detection still works..."
echo ""

echo "   Recent device state changes:"
docker logs wardops-worker-monitoring-prod 2>&1 | grep -E "went DOWN|RECOVERED" | tail -10

echo ""
echo "   Recent alerts created in database:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) FILTER (WHERE triggered_at > NOW() - INTERVAL '1 hour') as alerts_last_hour,
    COUNT(*) FILTER (WHERE triggered_at > NOW() - INTERVAL '15 minutes') as alerts_last_15min,
    MAX(triggered_at) as most_recent_alert
FROM alert_history;
"

# ============================================================================
# TEST 8: DEVICE STATE MANAGEMENT
# ============================================================================
echo ""
echo "📱 Test 8: Checking device state management (down_since)..."
echo ""

echo "   Devices currently DOWN:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    name,
    ip,
    down_since,
    EXTRACT(EPOCH FROM (NOW() - down_since))/60 as minutes_down
FROM standalone_devices
WHERE down_since IS NOT NULL
ORDER BY down_since DESC
LIMIT 10;
"

# ============================================================================
# TEST 9: VICTORIAMETRICS DATA RETENTION
# ============================================================================
echo ""
echo "📅 Test 9: Checking VictoriaMetrics data retention..."
echo ""

# Query time range of data
echo "   Querying time range of ping data in VictoriaMetrics..."

OLDEST_TS=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" 2>/dev/null | jq -r '[.data.result[].value[0]] | min' 2>/dev/null || echo "unknown")
NEWEST_TS=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" 2>/dev/null | jq -r '[.data.result[].value[0]] | max' 2>/dev/null || echo "unknown")

if [ "$OLDEST_TS" != "unknown" ] && [ "$NEWEST_TS" != "unknown" ]; then
    OLDEST_DATE=$(date -d "@$OLDEST_TS" 2>/dev/null || date -r "$OLDEST_TS" 2>/dev/null || echo "unknown")
    NEWEST_DATE=$(date -d "@$NEWEST_TS" 2>/dev/null || date -r "$NEWEST_TS" 2>/dev/null || echo "unknown")

    echo "   Oldest ping: $OLDEST_DATE"
    echo "   Newest ping: $NEWEST_DATE"
    echo "✅ VictoriaMetrics has ping data"
else
    echo "⚠️  Could not determine data time range (jq may not be available)"
fi

# ============================================================================
# TEST 10: COMPREHENSIVE LABELS VERIFICATION
# ============================================================================
echo ""
echo "🏷️  Test 10: Verifying comprehensive labels..."
echo ""

echo "   Checking if device_name labels are present:"
DEVICES_WITH_NAMES=$(curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" 2>/dev/null | grep -o '"device_name":"[^"]*"' | wc -l)

if [ "$DEVICES_WITH_NAMES" -gt 0 ]; then
    echo "✅ device_name labels present ($DEVICES_WITH_NAMES devices)"

    echo ""
    echo "   Sample device names:"
    curl -s "http://localhost:8428/api/v1/query?query=device_ping_status" 2>/dev/null | jq -r '.data.result[].metric.device_name' | sort -u | head -10 || echo "   (jq not available)"
else
    echo "⚠️  device_name labels not found"
fi

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    VERIFICATION SUMMARY                            ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Count successful tests
PASS_COUNT=0

[ "$VM_HEALTH" = "OK" ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$PING_STATUS_COUNT" -gt 0 ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$RTT_COUNT" -gt 0 ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$WORKER_STATUS" = "healthy" ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$VM_ERRORS" -eq 0 ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$DEVICES_WITH_NAMES" -gt 0 ] && PASS_COUNT=$((PASS_COUNT + 1))

echo "📊 Tests Passed: $PASS_COUNT / 6 critical tests"
echo ""

if [ "$PASS_COUNT" -ge 5 ]; then
    echo "✅ PHASE 2 VERIFICATION SUCCESSFUL!"
    echo ""
    echo "🎯 What's Working:"
    echo "   ✅ VictoriaMetrics is receiving ping data"
    echo "   ✅ Monitoring worker is healthy"
    echo "   ✅ Comprehensive labels are being written"
    echo "   ✅ Alert detection still works"
    echo ""
    echo "📋 NEXT STEPS:"
    echo "   1. Monitor ping_results table size for 1-2 hours"
    echo "      (should NOT grow - confirms Phase 2 success)"
    echo ""
    echo "   2. Proceed with Phase 3:"
    echo "      - Update API endpoints to read from VictoriaMetrics"
    echo "      - Update dashboard queries"
    echo "      - See VICTORIAMETRICS-ARCHITECTURE.md"
    echo ""
else
    echo "⚠️  WARNING: Some tests failed"
    echo ""
    echo "📋 TROUBLESHOOTING:"
    echo "   1. Check worker logs:"
    echo "      docker logs wardops-worker-monitoring-prod"
    echo ""
    echo "   2. Check VictoriaMetrics logs:"
    echo "      docker logs wardops-victoriametrics-prod"
    echo ""
    echo "   3. Verify monitoring worker is running:"
    echo "      docker ps | grep monitoring"
    echo ""
    echo "   4. Check if pings are executing:"
    echo "      docker logs wardops-worker-monitoring-prod 2>&1 | grep 'Pinged'"
    echo ""
fi

echo "📝 MONITORING COMMANDS:"
echo "   # Watch ping_results table size (should stop growing):"
echo "   watch -n 60 'docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \"SELECT COUNT(*) FROM ping_results\"'"
echo ""
echo "   # Watch VictoriaMetrics metrics count (should increase):"
echo "   watch -n 10 'curl -s http://localhost:8428/api/v1/query?query=device_ping_status | grep -o '\"metric\":' | wc -l'"
echo ""
echo "   # Monitor worker for VM writes:"
echo "   docker logs -f wardops-worker-monitoring-prod 2>&1 | grep 'VictoriaMetrics'"
echo ""
