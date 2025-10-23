#!/bin/bash

##############################################################################
# Deploy Diagnostic Logging for Ping Investigation
##############################################################################
#
# Purpose: Add detailed logging to trace why device 10.195.83.252 is not
#          being pinged despite being enabled in database
#
# Changes:
# - monitoring/tasks.py: Added comprehensive logging to ping_all_devices
# - monitoring/tasks.py: Added logging to ping_device for target IP
#
##############################################################################

set -e

echo "=========================================================================="
echo "DEPLOY DIAGNOSTIC LOGGING - PING INVESTIGATION"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production-local.yml"

##############################################################################
# Summary
##############################################################################
echo -e "${BLUE}🎯 Purpose:${NC}"
echo ""
echo "  Investigate why device 10.195.83.252 (PING-Kutaisi4-AP) is not being"
echo "  pinged despite being enabled in the database."
echo ""
echo -e "${BLUE}📝 Changes:${NC}"
echo ""
echo "  monitoring/tasks.py - ping_all_devices():"
echo "    - Log total devices retrieved from database"
echo "    - Log all device IPs to be pinged"
echo "    - Check specifically for target device 10.195.83.252"
echo "    - Log if device is found or missing from query results"
echo "    - Log total scheduled ping tasks"
echo ""
echo "  monitoring/tasks.py - ping_device():"
echo "    - Log when executing ping for target device"
echo ""
echo -e "${YELLOW}⚠️  This will restart worker and beat containers!${NC}"
echo ""

read -p "Press ENTER to continue (Ctrl+C to cancel)..."

##############################################################################
# Step 1: Rebuild Worker and Beat
##############################################################################
echo ""
echo -e "${BLUE}[1/3] Rebuilding worker and beat containers...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" build --no-cache celery-worker celery-beat

echo ""
echo -e "${GREEN}✅ Containers rebuilt${NC}"
echo ""

##############################################################################
# Step 2: Restart Containers
##############################################################################
echo ""
echo -e "${BLUE}[2/3] Restarting worker and beat...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" up -d celery-worker celery-beat

echo ""
echo "Waiting 20 seconds for startup..."
sleep 20

echo ""
echo -e "${GREEN}✅ Containers restarted${NC}"
echo ""

##############################################################################
# Step 3: Monitor Logs
##############################################################################
echo ""
echo -e "${BLUE}[3/3] Monitoring logs for diagnostic output...${NC}"
echo ""

echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(worker|beat|NAME)"

echo ""
echo "Waiting for next ping_all_devices execution (happens every 30 seconds)..."
echo ""

# Wait for 35 seconds to ensure at least one ping cycle happens
sleep 35

echo ""
echo "Recent worker logs (looking for diagnostic output):"
echo ""
docker logs wardops-worker-prod --tail 100 | grep -E "(ping_all_devices|Retrieved.*devices|Device IPs to ping|Target device|10.195.83.252)"

echo ""
echo "Recent beat logs (scheduler):"
echo ""
docker logs wardops-beat-prod --tail 20 | grep "ping-all-devices"

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ DIAGNOSTIC LOGGING DEPLOYED${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}🔍 Next Steps:${NC}"
echo ""
echo "1. Monitor worker logs for the next 2-3 minutes:"
echo "   docker logs wardops-worker-prod -f | grep -E '(ping_all_devices|10.195.83.252)'"
echo ""
echo "2. Look for these diagnostic messages:"
echo "   - 'Retrieved X enabled devices from database'"
echo "   - 'Device IPs to ping: [...]'"
echo "   - 'Found target device 10.195.83.252' OR"
echo "   - 'Target device 10.195.83.252 NOT FOUND'"
echo "   - 'Scheduled X ping tasks'"
echo ""
echo "3. If device is NOT FOUND:"
echo "   - Check if it exists but enabled=false"
echo "   - Check total device count vs enabled count"
echo ""
echo "4. If device IS FOUND but not pinged:"
echo "   - Look for 'EXECUTING ping for TARGET device'"
echo "   - If missing, there's an issue in the scheduling logic"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

exit 0
