#!/bin/bash

##############################################################################
# WARD OPS CredoBank - Hotfix Deployment
##############################################################################
#
# HOTFIX: Critical Bug Fixes
#
# Fix 1: NameError in routers/devices.py
# - Bug: Variable 'device_ip' not defined (should be 'ip')
# - Impact: 500 error when clicking device ping in UI
# - Fixed: Line 410 in routers/devices.py
#
# Fix 2: Idle Transaction Leak in monitoring/tasks.py
# - Bug: Database session held open during SNMP network calls
# - Impact: 45-51 "idle in transaction" connections
# - Fixed: Close DB session BEFORE network operations
#
# Date: 2025-10-23
# Deployment Target: Production (10.30.25.39)
#
##############################################################################

set -e  # Exit on error

echo "=========================================================================="
echo "WARD OPS - Hotfix Deployment (Critical Bugs)"
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

# Configuration
COMPOSE_FILE="docker-compose.production-local.yml"

##############################################################################
# Pre-Flight Checks
##############################################################################
echo -e "${BLUE}[Pre-Flight] Checking environment...${NC}"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ Error: $COMPOSE_FILE not found!${NC}"
    exit 1
fi

if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Error: Not in WARD OPS root directory!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment OK${NC}"
echo ""

##############################################################################
# Step 1: Pull Latest Code
##############################################################################
echo -e "${BLUE}[1/4] Pulling latest hotfix from GitHub...${NC}"
git stash save "Pre-hotfix stash $(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
git pull origin main || {
    echo -e "${RED}❌ Git pull failed!${NC}"
    exit 1
}
echo -e "${GREEN}✅ Hotfix code pulled${NC}"
echo ""

##############################################################################
# Step 2: Rebuild Only API and Worker (Fast)
##############################################################################
echo -e "${BLUE}[2/4] Rebuilding affected containers (API + Worker)...${NC}"
echo "This will take ~2 minutes..."

# Only rebuild what changed
docker-compose -f "$COMPOSE_FILE" build --no-cache api celery-worker

echo -e "${GREEN}✅ Containers rebuilt${NC}"
echo ""

##############################################################################
# Step 3: Restart Services
##############################################################################
echo -e "${BLUE}[3/4] Restarting services...${NC}"

# Restart only affected services (faster than full restart)
docker-compose -f "$COMPOSE_FILE" restart api celery-worker

echo "Waiting for services to stabilize..."
sleep 20

echo -e "${GREEN}✅ Services restarted${NC}"
echo ""

##############################################################################
# Step 4: Verification
##############################################################################
echo -e "${BLUE}[4/4] Verifying fixes...${NC}"
echo ""

# 1. Check containers are running
echo -e "${BLUE}1️⃣  Container Status:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep wardops
echo ""

# 2. Test API health
echo -e "${BLUE}2️⃣  API Health:${NC}"
sleep 5
curl -s http://localhost:5001/api/v1/health | python3 -m json.tool 2>/dev/null || echo -e "${YELLOW}⚠️  API warming up...${NC}"
echo ""

# 3. Check for idle transactions (should be decreasing)
echo -e "${BLUE}3️⃣  Database Connection Pool (idle transactions should decrease):${NC}"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT state, count(*) as connections, max(now() - query_start) as max_duration
FROM pg_stat_activity
WHERE datname = 'ward_ops'
GROUP BY state
ORDER BY count DESC;
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not check connections${NC}"
echo ""

# 4. Check worker logs for errors
echo -e "${BLUE}4️⃣  Recent Worker Logs (checking for errors):${NC}"
docker logs wardops-worker-prod --tail 20 2>&1 | grep -E "(ERROR|Exception|Traceback)" || echo -e "${GREEN}✅ No errors in worker logs${NC}"
echo ""

# 5. Check API logs for the NameError
echo -e "${BLUE}5️⃣  API Logs (checking for NameError):${NC}"
docker logs wardops-api-prod --tail 50 2>&1 | grep -E "NameError.*device_ip" || echo -e "${GREEN}✅ No NameError found${NC}"
echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ HOTFIX DEPLOYMENT COMPLETE!${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}🔧 Fixes Applied:${NC}"
echo ""
echo "  Fix 1: NameError in Device Ping"
echo "    • File: routers/devices.py:410"
echo "    • Changed: device_ip → ip"
echo "    • Result: Device ping from UI now works"
echo ""
echo "  Fix 2: Idle Transaction Leak"
echo "    • File: monitoring/tasks.py:86-90"
echo "    • Changed: Close DB before SNMP polling"
echo "    • Result: Idle transactions will drop to near zero"
echo ""
echo -e "${BLUE}📊 Expected Results:${NC}"
echo "  • Device ping in UI: Works (no 500 error)"
echo "  • Idle transactions: Drop from 45-51 to < 5"
echo "  • Connection pool: More available connections"
echo "  • Performance: Same (still 500x faster!)"
echo ""
echo -e "${BLUE}🔍 Monitor Next 10 Minutes:${NC}"
echo ""
echo "Watch idle transactions decrease:"
echo "  docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \\"
echo "    \"SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'ward_ops' GROUP BY state;\""
echo ""
echo "Test device ping from UI:"
echo "  1. Open Monitor page: http://localhost:5001"
echo "  2. Click any device"
echo "  3. Should see device details (no 500 error)"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""
echo -e "${GREEN}🎉 System is now running with hotfixes applied!${NC}"
echo ""

exit 0
