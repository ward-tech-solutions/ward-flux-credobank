#!/bin/bash
#######################################################
# Verify Cache Clearing Fix is Working
#######################################################

echo "=========================================="
echo "  CACHE FIX VERIFICATION"
echo "  $(date)"
echo "=========================================="
echo ""

# 1. Check if worker is running
echo "=== 1. WORKER STATUS ==="
docker ps | grep -E "NAME|wardops-worker-monitoring"
echo ""

# 2. Check worker startup logs
echo "=== 2. WORKER STARTUP (Last 30 lines) ==="
docker logs --tail=30 wardops-worker-monitoring-prod
echo ""

# 3. Check for cache clearing in logs
echo "=== 3. CACHE CLEARING ACTIVITY (Last 5 minutes) ==="
docker logs --since 5m wardops-worker-monitoring-prod 2>&1 | grep -i cache | tail -20
if [ $? -ne 0 ]; then
    echo "No cache activity yet (waiting for device status change)"
fi
echo ""

# 4. Check recent ping activity
echo "=== 4. RECENT PING ACTIVITY (Last 2 minutes) ==="
docker logs --since 2m wardops-worker-monitoring-prod 2>&1 | grep -E "Batch processed|went DOWN|RECOVERED" | tail -15
echo ""

# 5. Watch for next status change
echo "=== 5. WAITING FOR NEXT STATUS CHANGE (30 seconds) ==="
echo "Watching for device status changes and cache clears..."
timeout 30 docker logs -f wardops-worker-monitoring-prod 2>&1 | grep -E "went DOWN|RECOVERED|Cleared.*cache" &
PID=$!
sleep 30
kill $PID 2>/dev/null
echo ""

echo "=========================================="
echo "  VERIFICATION COMPLETE"
echo "=========================================="
echo ""
echo "What to look for:"
echo "  ✅ Worker status: Up and healthy"
echo "  ✅ Ping batches processing every 10 seconds"
echo "  ✅ When device goes DOWN: 'Cleared X cache entries' message"
echo "  ✅ When device comes UP: 'Cleared X cache entries' message"
echo ""
echo "If you don't see cache clearing yet, it's because no"
echo "devices have changed status. The cache will clear on"
echo "the next status change (UP→DOWN or DOWN→UP)."
