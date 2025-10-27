#!/bin/bash

# WARD FLUX - Deploy Celery Beat Queue Fix
# Fixes interface metrics collection task routing to SNMP queue

set -e

echo "=============================================="
echo "WARD FLUX - Celery Beat Queue Fix Deployment"
echo "=============================================="
echo ""
echo "This deployment fixes the interface metrics collection task"
echo "routing so it goes to the SNMP queue instead of default queue."
echo ""
echo "Changes:"
echo "  ✅ celery_app.py - Added queue options to beat_schedule"
echo "  ✅ Task 'collect-interface-metrics' now routes to SNMP queue"
echo ""
echo "Expected Result:"
echo "  - VictoriaMetrics will start receiving interface metrics"
echo "  - Metrics will appear within 2-3 minutes"
echo "  - Bandwidth data available for topology display"
echo ""
read -p "Press ENTER to continue or CTRL+C to cancel..."

# Stop Celery Beat and SNMP worker
echo ""
echo "1. Stopping Celery Beat and SNMP worker..."
docker-compose -f docker-compose.production-priority-queues.yml stop celery-beat celery-worker-snmp

# Remove old containers
echo "2. Removing old containers..."
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-beat celery-worker-snmp

# Rebuild Beat container with fix
echo "3. Building Celery Beat with queue fix..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache celery-beat

# Start containers
echo "4. Starting Celery Beat and SNMP worker..."
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-beat celery-worker-snmp

# Wait for startup
echo "5. Waiting for containers to start..."
sleep 10

# Check container status
echo "6. Checking container status..."
docker-compose -f docker-compose.production-priority-queues.yml ps celery-beat celery-worker-snmp

echo ""
echo "=============================================="
echo "Deployment Complete!"
echo "=============================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Wait 2-3 minutes for metrics to start collecting"
echo "   (Celery task runs every 60 seconds)"
echo ""
echo "2. Verify VictoriaMetrics has data:"
echo "   curl -s 'http://localhost:8428/api/v1/query?query=count(interface_if_hc_in_octets)' | jq ."
echo ""
echo "3. Check specific device metrics:"
echo "   curl -s 'http://localhost:8428/api/v1/query?query=interface_if_hc_in_octets{device_ip=\"10.195.57.5\"}' | jq ."
echo ""
echo "4. Monitor Celery logs:"
echo "   docker logs -f wardops-worker-snmp-prod"
echo ""
echo "Expected in logs:"
echo "   'Collecting interface metrics for all devices...'"
echo "   'Collected metrics for device X interfaces...'"
echo ""
echo "If metrics appear, proceed with topology deployment:"
echo "   bash deploy-topology-complete.sh"
echo ""
