#!/bin/bash
set -e

echo "=========================================="
echo "Fix Container and Deploy ISP Monitoring"
echo "$(date)"
echo "=========================================="
echo ""

cd /home/wardops/ward-flux-credobank

echo "Step 1: Pull latest code..."
git pull origin main

echo ""
echo "Step 2: Stop and remove SNMP worker..."
docker-compose -f docker-compose.production-priority-queues.yml stop celery-worker-snmp || true
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-worker-snmp || true

echo ""
echo "Step 3: Remove any orphaned containers..."
docker rm -f wardops-worker-snmp-prod 2>/dev/null || true

echo ""
echo "Step 4: Rebuild image..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache celery-worker-snmp

echo ""
echo "Step 5: Start SNMP worker..."
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-worker-snmp

echo ""
echo "Step 6: Wait for worker initialization..."
sleep 10

echo ""
echo "Step 7: Test SNMP imports..."
docker exec wardops-worker-snmp-prod python3 -c "
import sys
import warnings
sys.path.insert(0, '/app')
warnings.filterwarnings('ignore', category=DeprecationWarning)

from pysnmp.hlapi.asyncio import getCmd, bulkCmd, nextCmd
print('✅ pysnmp imports work')

from monitoring.snmp.poller import SNMPPoller
print('✅ SNMPPoller imports work')

poller = SNMPPoller(timeout=5, retries=2)
print('✅ SNMPPoller instantiation works')
print('')
print('🎉 READY FOR INTERFACE DISCOVERY')
"

echo ""
echo "=========================================="
echo "✅ SNMP Worker Ready"
echo "=========================================="
echo ""
echo "Now running interface discovery..."
echo ""

./deploy-isp-monitoring.sh
