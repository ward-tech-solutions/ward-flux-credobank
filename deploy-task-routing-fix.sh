#!/bin/bash
#
# CRITICAL FIX: Add task routing for interface metrics collection
#
# ROOT CAUSE: celery_app.py had the correct task name in beat_schedule
# but was MISSING task routing configuration, so tasks were going to
# default queue instead of 'snmp' queue where the SNMP worker listens.
#
# This script:
# 1. Stops Beat and SNMP worker
# 2. Removes old containers
# 3. Pulls latest code with task routing
# 4. Starts containers back up
# 5. Monitors logs to verify task is routed correctly
#

set -e  # Exit on any error

echo "=========================================="
echo "CRITICAL FIX: Task Routing Configuration"
echo "=========================================="
echo ""
echo "Adding task routing for interface metrics..."
echo ""

# Navigate to project directory
cd /home/wardops/ward-flux-credobank

echo "[1/5] Pulling latest code from main branch..."
git pull origin main

echo ""
echo "[2/5] Stopping affected containers (Beat + SNMP worker)..."
docker-compose -f docker-compose.production-priority-queues.yml stop celery-beat celery-worker-snmp

echo ""
echo "[3/5] Removing old containers..."
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-beat celery-worker-snmp

echo ""
echo "[4/5] Starting containers with new configuration..."
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-beat celery-worker-snmp

echo ""
echo "[5/5] Waiting 10 seconds for containers to start..."
sleep 10

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Verifying task execution..."
echo ""

# Wait for Beat to send the task (happens every 60 seconds)
echo "Waiting 60 seconds for Beat to send the task..."
sleep 60

# Check Beat logs
echo ""
echo "=== BEAT SCHEDULER LOGS ==="
docker logs --tail 30 wardops-beat-prod 2>&1 | grep -E "collect-interface-metrics|Sending due task" | tail -5

echo ""
echo "=== SNMP WORKER LOGS ==="
docker logs --tail 50 wardops-worker-snmp-prod 2>&1 | grep -E "collect_all_interface_metrics|Collecting interface metrics" | tail -10

echo ""
echo "=========================================="
echo "VERIFICATION:"
echo "=========================================="
echo ""
echo "If you see 'Task monitoring.tasks.collect_all_interface_metrics[...] received' above,"
echo "then the fix is working!"
echo ""
echo "Wait 2-3 minutes, then check VictoriaMetrics:"
echo "  curl -s \"http://localhost:8428/api/v1/query?query=interface_oper_status{isp_provider!=\\\"\\\"}\" | jq ."
echo ""
echo "Expected: Non-empty result with interface metrics"
echo ""
echo "Then check the UI - ISP badges on 10.195.57.5 should turn GREEN"
echo ""
