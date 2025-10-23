#!/bin/bash

##############################################################################
# WARD OPS - Start Celery Workers
##############################################################################
#
# Issue: Celery workers not running - causes 6 minute delays in status updates
# Fix: Start celery-worker and celery-beat containers
#
##############################################################################

set -e

echo "=========================================================================="
echo "WARD OPS - Starting Celery Workers"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production-local.yml"

##############################################################################
# Step 1: Check Current Status
##############################################################################
echo -e "${BLUE}[1/4] Checking current Celery status...${NC}"
echo ""

echo "Current container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(celery|NAME)" || echo "No celery containers running"

echo ""

##############################################################################
# Step 2: Start Celery Workers
##############################################################################
echo -e "${BLUE}[2/4] Starting Celery workers...${NC}"
echo ""

# Start celery-worker and celery-beat
docker-compose -f "$COMPOSE_FILE" up -d celery-worker celery-beat

echo ""
echo "Waiting for workers to start..."
sleep 10

echo -e "${GREEN}✅ Workers started${NC}"
echo ""

##############################################################################
# Step 3: Verify Workers Are Running
##############################################################################
echo -e "${BLUE}[3/4] Verifying workers...${NC}"
echo ""

echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(celery|NAME)"

echo ""
echo "Celery worker logs (last 20 lines):"
docker logs wardops-worker-prod --tail 20 2>&1 | tail -20

echo ""
echo "Celery beat logs (last 20 lines):"
docker logs wardops-beat-prod --tail 20 2>&1 | tail -20

echo ""

##############################################################################
# Step 4: Test Ping Task
##############################################################################
echo -e "${BLUE}[4/4] Testing ping task execution...${NC}"
echo ""

echo "Waiting 35 seconds for first ping cycle..."
sleep 35

echo ""
echo "Checking for recent ping activity in worker logs:"
docker logs wardops-worker-prod --tail 50 2>&1 | grep -i "ping" | tail -10 || echo "No ping activity yet (may need more time)"

echo ""
echo "Checking latest ping results in database:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT device_name, device_ip, is_reachable, timestamp, NOW() - timestamp AS age
FROM ping_results
ORDER BY timestamp DESC
LIMIT 10;
" 2>/dev/null || echo "Could not query database"

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ CELERY WORKERS STARTED!${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}🎯 What Was Fixed:${NC}"
echo ""
echo "  Problem: Celery workers not running"
echo "  Impact: 6 minute delays in device status updates"
echo "  Solution: Started celery-worker and celery-beat containers"
echo ""
echo -e "${BLUE}📊 Expected Results:${NC}"
echo ""
echo "  • Ping tasks now running every 30 seconds"
echo "  • Device status updates within 30-60 seconds"
echo "  • Alerts created immediately when devices go DOWN"
echo "  • Real-time monitoring fully functional"
echo ""
echo -e "${BLUE}🔍 Monitor Next 5 Minutes:${NC}"
echo ""
echo "1. Watch celery logs:"
echo "   docker logs wardops-worker-prod -f | grep ping"
echo ""
echo "2. Check ping results are updating:"
echo "   watch -n 5 'docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \"SELECT device_name, timestamp, NOW() - timestamp AS age FROM ping_results ORDER BY timestamp DESC LIMIT 5;\"'"
echo ""
echo "3. Test with a device:"
echo "   - Disconnect a test device network cable"
echo "   - Wait 30-60 seconds"
echo "   - Check if dashboard shows RED status"
echo "   - Reconnect device"
echo "   - Wait 30-60 seconds"
echo "   - Check if dashboard shows GREEN status"
echo ""
echo -e "${BLUE}⚠️  Why Did This Happen?${NC}"
echo ""
echo "Celery workers may have stopped due to:"
echo "  • Server reboot (workers not set to auto-restart)"
echo "  • Container crash (out of memory, error)"
echo "  • Manual stop (someone ran 'docker stop')"
echo "  • Docker daemon restart"
echo ""
echo "To prevent this in the future:"
echo "  • Check docker-compose restart policy"
echo "  • Monitor Celery worker health"
echo "  • Add alerting for worker failures"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""
echo -e "${GREEN}🎉 Real-time monitoring should now be working!${NC}"
echo ""

exit 0
