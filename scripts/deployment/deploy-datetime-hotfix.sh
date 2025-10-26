#!/bin/bash

##############################################################################
# WARD OPS - Critical Datetime Bug Hotfix Deployment
##############################################################################
#
# Issue: Ping tasks failing with datetime.timezone AttributeError
# Impact: Real-time monitoring completely broken
# Fix: Remove shadowing datetime import in monitoring/tasks.py
#
##############################################################################

set -e

echo "=========================================================================="
echo "WARD OPS - Critical Datetime Bug Hotfix"
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
# Step 1: Show Current Issue
##############################################################################
echo -e "${RED}[1/5] Current Issue in Production:${NC}"
echo ""
echo "Error in worker logs:"
echo "  Failed to save ping record: datetime.datetime has no attribute 'timezone'"
echo ""
echo "Impact:"
echo "  ❌ Ping results NOT being saved"
echo "  ❌ Device status NOT updating"
echo "  ❌ Alerts NOT being created"
echo "  ❌ Real-time monitoring completely broken"
echo ""
echo -e "${BLUE}Checking current worker logs for errors...${NC}"
docker logs wardops-worker-prod --tail 100 2>&1 | grep -E "(Failed to save|AttributeError)" | tail -5 || echo "No errors found (or container not accessible)"
echo ""

##############################################################################
# Step 2: Rebuild Worker Container
##############################################################################
echo -e "${BLUE}[2/5] Rebuilding worker container with fix...${NC}"
echo ""

# Build fresh image
docker-compose -f "$COMPOSE_FILE" build --no-cache celery-worker

echo ""
echo -e "${GREEN}✅ Worker container rebuilt${NC}"
echo ""

##############################################################################
# Step 3: Stop Old Containers
##############################################################################
echo -e "${BLUE}[3/5] Stopping old worker and beat containers...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" stop celery-worker celery-beat
docker-compose -f "$COMPOSE_FILE" rm -f celery-worker celery-beat

echo ""
echo -e "${GREEN}✅ Old containers stopped and removed${NC}"
echo ""

##############################################################################
# Step 4: Start New Containers
##############################################################################
echo -e "${BLUE}[4/5] Starting new worker and beat containers...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" up -d celery-worker celery-beat

echo ""
echo "Waiting 15 seconds for workers to start..."
sleep 15

echo ""
echo -e "${GREEN}✅ New containers started${NC}"
echo ""

##############################################################################
# Step 5: Verify Fix
##############################################################################
echo -e "${BLUE}[5/5] Verifying fix...${NC}"
echo ""

echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(worker|beat|NAME)"

echo ""
echo "Worker logs (last 30 lines):"
docker logs wardops-worker-prod --tail 30 2>&1

echo ""
echo "Beat logs (last 20 lines):"
docker logs wardops-beat-prod --tail 20 2>&1

echo ""
echo "Waiting 35 seconds for first ping cycle..."
sleep 35

echo ""
echo "Checking for successful ping tasks (should see NO errors):"
docker logs wardops-worker-prod --tail 50 2>&1 | grep -i "ping" | tail -20 || echo "No ping activity yet"

echo ""
echo "Checking latest ping results in database:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT device_name, device_ip, is_reachable, timestamp, NOW() - timestamp AS age
FROM ping_results
ORDER BY timestamp DESC
LIMIT 10;
" 2>/dev/null || echo "Could not query database"

echo ""
echo "Checking for datetime errors (should be EMPTY):"
docker logs wardops-worker-prod --tail 100 2>&1 | grep -E "(Failed to save|AttributeError|timezone)" || echo -e "${GREEN}✅ No datetime errors found!${NC}"

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ CRITICAL DATETIME HOTFIX DEPLOYED!${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}🎯 What Was Fixed:${NC}"
echo ""
echo "  Problem: Shadowing datetime import in monitoring/tasks.py"
echo "  Error: type object 'datetime.datetime' has no attribute 'timezone'"
echo "  Impact: Ping tasks failing, real-time monitoring broken"
echo "  Solution: Removed local 'from datetime import datetime' that shadowed module import"
echo ""
echo -e "${BLUE}📊 Expected Results:${NC}"
echo ""
echo "  ✅ Ping tasks now succeed (no more datetime errors)"
echo "  ✅ Ping results saved to database every 30 seconds"
echo "  ✅ Device status updates within 30-60 seconds"
echo "  ✅ Alerts created immediately when devices go DOWN"
echo "  ✅ Real-time monitoring fully functional"
echo ""
echo -e "${BLUE}🔍 Verify Next 2 Minutes:${NC}"
echo ""
echo "1. Watch worker logs for ping tasks (should succeed):"
echo "   docker logs wardops-worker-prod -f | grep -E '(ping|Failed)'"
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
echo -e "${BLUE}📝 Root Cause:${NC}"
echo ""
echo "The idle transaction hotfix (commit fb30bdd) added a local import:"
echo "  from datetime import datetime"
echo ""
echo "This shadowed the module-level import:"
echo "  from datetime import datetime, timedelta, timezone"
echo ""
echo "When line 236 tried to use timezone.utc, Python looked for"
echo "datetime.timezone, but datetime was the class (not module)!"
echo ""
echo "Fix: Removed the shadowing local import."
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""
echo -e "${GREEN}🎉 Real-time monitoring should now be working!${NC}"
echo ""
echo -e "${YELLOW}⚠️  Monitor worker logs for 5 minutes to ensure no errors.${NC}"
echo ""

exit 0
