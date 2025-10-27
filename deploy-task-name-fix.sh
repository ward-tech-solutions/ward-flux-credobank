#!/bin/bash
#
# CRITICAL FIX: Deploy corrected Celery task names
#
# ROOT CAUSE: Beat scheduler was sending tasks with wrong names
# - Beat sent: monitoring.tasks_interface_metrics.collect_all_interface_metrics_task
# - Worker registered: monitoring.tasks.collect_all_interface_metrics
# - Result: Worker NEVER received the task!
#
# This script:
# 1. Stops Beat and SNMP worker (affected containers)
# 2. Removes old containers
# 3. Rebuilds with new celery_app configuration
# 4. Starts containers back up
# 5. Monitors logs to verify task is now being received
#

set -e  # Exit on any error

echo "=========================================="
echo "CRITICAL FIX: Celery Task Name Mismatch"
echo "=========================================="
echo ""
echo "Deploying fix for interface metrics collection..."
echo ""

# Navigate to project directory
cd /home/wardops/ward-flux-credobank

echo "[1/6] Pulling latest code from main branch..."
git pull origin main

echo ""
echo "[2/6] Stopping affected containers (Beat + SNMP worker)..."
docker-compose -f docker-compose.production-priority-queues.yml stop celery-beat celery-worker-snmp

echo ""
echo "[3/6] Removing old containers..."
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-beat celery-worker-snmp

echo ""
echo "[4/6] Rebuilding containers with corrected task names..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache celery-beat celery-worker-snmp

echo ""
echo "[5/6] Starting containers..."
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-beat celery-worker-snmp

echo ""
echo "[6/6] Waiting 10 seconds for containers to start..."
sleep 10

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Verifying task execution..."
echo ""

# Check Beat logs to see if task is being sent
echo "=== BEAT SCHEDULER LOGS (last 30 lines) ==="
docker logs --tail 30 wardops-celery-beat-prod | grep -E "(collect-interface-metrics|collect_all_interface_metrics)" || echo "No matching logs yet (will appear in next 60 seconds)"

echo ""
echo "=== SNMP WORKER LOGS (last 30 lines) ==="
docker logs --tail 30 wardops-worker-snmp-prod | grep -E "(collect_all_interface_metrics|Task.*received)" || echo "No task reception logs yet (will appear in next 60 seconds)"

echo ""
echo "=========================================="
echo "VERIFICATION STEPS:"
echo "=========================================="
echo ""
echo "1. Wait 60 seconds for Beat to send the task"
echo ""
echo "2. Check worker logs for task reception:"
echo "   docker logs -f wardops-worker-snmp-prod"
echo ""
echo "   EXPECTED LOG:"
echo "   [INFO/MainProcess] Task monitoring.tasks.collect_all_interface_metrics[...] received"
echo ""
echo "3. After 2-3 minutes, verify VictoriaMetrics has data:"
echo "   curl -s \"http://localhost:8428/api/v1/query?query=interface_oper_status{isp_provider!=\\\"\\\"}\" | jq ."
echo ""
echo "   EXPECTED: Non-empty result with interface status metrics"
echo ""
echo "4. Open Monitor page (http://10.30.25.46:5001/monitor)"
echo "   - Search for \".5\" routers"
echo "   - ISP badges should turn GREEN for working links"
echo ""
echo "=========================================="
echo ""
