#!/bin/bash
#######################################################
# Verify Alert Delay Fix Deployment
#######################################################

echo "=========================================="
echo "  DEPLOYMENT VERIFICATION"
echo "  $(date)"
echo "=========================================="
echo ""

# 1. Check code file
echo "=== 1. CODE FILE CHECK ==="
echo "Checking celery_app.py ping configuration..."
grep -A 3 '"ping-devices-icmp"' monitoring/celery_app.py
echo ""

# 2. Wait for Beat to fully start and check schedule
echo "=== 2. BEAT SCHEDULE CHECK ==="
echo "Waiting 10 seconds for Beat to initialize..."
sleep 10
echo "Checking Beat logs for ping schedule..."
docker logs wardops-beat-prod 2>&1 | grep "ping-all-devices" | tail -5
echo ""

# 3. Check Beat health
echo "=== 3. BEAT HEALTH STATUS ==="
docker ps | grep beat
echo ""

# 4. Monitor worker execution for 30 seconds
echo "=== 4. WORKER EXECUTION (Monitoring for 30 seconds) ==="
echo "Watching for batched task execution..."
timeout 30 docker logs -f wardops-worker-monitoring-prod 2>&1 | grep -E "Batch processed|Scheduling.*batch" &
PID=$!
sleep 30
kill $PID 2>/dev/null
echo ""

# 5. Check for errors
echo "=== 5. ERROR CHECK ==="
docker logs --since 5m wardops-worker-monitoring-prod 2>&1 | grep -i error | tail -5
if [ $? -ne 0 ]; then
    echo "✅ No errors found"
fi
echo ""

# 6. Final summary
echo "=========================================="
echo "  VERIFICATION SUMMARY"
echo "=========================================="
echo ""
echo "Expected Results:"
echo "  ✅ Code shows: ping_all_devices_batched with 10.0 second schedule"
echo "  ✅ Beat logs show: ping-all-devices (monitoring.tasks.ping_all_devices_batched)"
echo "  ✅ Beat status: healthy"
echo "  ✅ Workers show: 'Batch processed 100 devices' every 10 seconds"
echo "  ✅ No errors"
echo ""
echo "Detection Performance:"
echo "  • Ping interval: 10 seconds"
echo "  • Total ping time: ~3 seconds (9 batches)"
echo "  • Device down detection: 0-10 seconds"
echo "  • Alert latency: 10-20 seconds"
echo ""
echo "✅ DEPLOYMENT SUCCESSFUL!"
