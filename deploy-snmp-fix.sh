#!/bin/bash
# Deploy SNMP API Fix
# Fixes ImportError by using correct pysnmp-lextudio v3arch.asyncio API

set -e

echo "=========================================="
echo "SNMP API Fix Deployment"
echo "$(date)"
echo "=========================================="
echo ""

# Step 1: Pull latest code
echo "Step 1: Pulling latest code from main..."
git pull origin main

# Step 2: Stop SNMP worker
echo ""
echo "Step 2: Stopping SNMP worker..."
docker-compose -f docker-compose.production-priority-queues.yml stop celery-worker-snmp

# Step 3: Remove container
echo "Step 3: Removing SNMP worker container..."
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-worker-snmp

# Step 4: Rebuild with no cache to ensure fresh build
echo ""
echo "Step 4: Building SNMP worker with new API fixes..."
docker-compose -f docker-compose.production-priority-queues.yml build --no-cache celery-worker-snmp

# Step 5: Start SNMP worker
echo ""
echo "Step 5: Starting SNMP worker..."
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-worker-snmp

echo ""
echo "✅ SNMP worker rebuilt with correct pysnmp-lextudio API!"
echo ""

# Step 6: Wait for worker to start
echo "Step 6: Waiting for worker to initialize..."
sleep 10

# Step 7: Test SNMP import
echo ""
echo "Step 7: Testing SNMP imports..."
docker exec wardops-worker-snmp-prod python3 -c "
import sys
sys.path.insert(0, '/app')

print('Testing pysnmp-lextudio imports...')
try:
    from pysnmp.hlapi.v3arch.asyncio import get_cmd, bulk_cmd, next_cmd
    print('✅ SUCCESS: pysnmp.hlapi.v3arch.asyncio imports work!')
except Exception as e:
    print(f'❌ FAILED: {e}')
    sys.exit(1)

print('')
print('Testing SNMP poller module...')
try:
    from monitoring.snmp.poller import SNMPPoller
    print('✅ SUCCESS: SNMPPoller imports successfully!')
except Exception as e:
    print(f'❌ FAILED: {e}')
    sys.exit(1)

print('')
print('All imports successful!')
"

echo ""
echo "=========================================="
echo "Next: Run Interface Discovery"
echo "=========================================="
echo ""
echo "The SNMP API fix is deployed. Now run interface discovery:"
echo ""
echo "  ./deploy-isp-monitoring.sh"
echo ""
echo "This will discover ISP interfaces on all 93 .5 routers."
echo ""
