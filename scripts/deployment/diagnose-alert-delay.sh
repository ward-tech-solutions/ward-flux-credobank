#!/bin/bash
#######################################################
# Alert Delay Diagnostic Script
# Run this on production server to diagnose the issue
#######################################################

echo "=========================================="
echo "  ALERT DELAY DIAGNOSTIC"
echo "  $(date)"
echo "=========================================="
echo ""

# 1. Check what's in the actual deployed code
echo "=== 1. DEPLOYED CODE CHECK ==="
echo "Checking celery_app.py ping task configuration..."
grep -A 3 '"ping-devices-icmp"' monitoring/celery_app.py
echo ""

# 2. Check Beat schedule from logs
echo "=== 2. BEAT SCHEDULE (Last 5 occurrences) ==="
docker logs wardops-beat-prod 2>&1 | grep "ping-all-devices" | tail -5
echo ""

# 3. Check if batched task module exists
echo "=== 3. BATCHED TASK MODULE CHECK ==="
if [ -f "monitoring/tasks_batch.py" ]; then
    echo "✅ tasks_batch.py EXISTS"
    echo "   File size: $(wc -l < monitoring/tasks_batch.py) lines"
    echo "   Functions:"
    grep "^def " monitoring/tasks_batch.py | head -10
else
    echo "❌ tasks_batch.py NOT FOUND"
fi
echo ""

# 4. Check worker logs for actual task execution
echo "=== 4. WORKER TASK EXECUTION (Last 30 seconds) ==="
echo "Looking for batched task execution..."
docker logs --since 30s wardops-worker-monitoring-prod 2>&1 | grep -E "ping_all_devices_batched|ping_devices_batch|Batch processed|Scheduling.*batch" | head -20
if [ $? -ne 0 ]; then
    echo "⚠️  No batched task execution found in last 30 seconds"
    echo ""
    echo "Checking for NON-batched individual ping tasks..."
    docker logs --since 30s wardops-worker-monitoring-prod 2>&1 | grep "ping_device" | head -10
fi
echo ""

# 5. Check for task failures
echo "=== 5. RECENT TASK ERRORS ==="
docker logs --since 5m wardops-worker-monitoring-prod 2>&1 | grep -E "ERROR|Exception|Failed|Traceback" | tail -10
if [ $? -ne 0 ]; then
    echo "✅ No errors in last 5 minutes"
fi
echo ""

# 6. Check worker resource usage
echo "=== 6. WORKER RESOURCE USAGE ==="
docker stats --no-stream | grep -E "NAME|wardops-worker-monitoring"
echo ""

# 7. Check task routing
echo "=== 7. CELERY TASK REGISTRATION ==="
echo "Checking if worker knows about batched tasks..."
docker exec wardops-worker-monitoring-prod celery -A monitoring.celery_app inspect registered 2>&1 | grep -E "ping_all_devices|ping_devices_batch" | head -10
echo ""

# 8. Check actual ping timing
echo "=== 8. PING TIMING ANALYSIS ==="
echo "Checking timestamps of ping task executions..."
docker logs --since 2m wardops-worker-monitoring-prod 2>&1 | grep "Received task.*ping" | tail -20
echo ""

# 9. Check Beat health
echo "=== 9. BEAT CONTAINER HEALTH ==="
docker ps | grep beat
docker inspect wardops-beat-prod --format='Health: {{.State.Health.Status}}'
echo ""

# 10. Check git status on server
echo "=== 10. GIT STATUS ==="
echo "Current branch:"
git branch --show-current
echo ""
echo "Last commit:"
git log --oneline -1
echo ""
echo "Uncommitted changes:"
git status --short
echo ""

echo "=========================================="
echo "  DIAGNOSIS COMPLETE"
echo "=========================================="
echo ""
echo "NEXT: Share this output so we can identify the issue!"
