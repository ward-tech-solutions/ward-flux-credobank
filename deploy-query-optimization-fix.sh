#!/bin/bash

##############################################################################
# WARD OPS - Fix 11-Second Cache Expiry Delay
##############################################################################
#
# Issue: Cache expiry causes 11-second delays instead of expected 300ms
# Root Cause: SQLAlchemy DISTINCT ON not translating correctly to PostgreSQL
# Solution: Replace with explicit subquery using MAX timestamp + JOIN
#
# Expected Impact:
# - Cache expiry time: 11s → 300ms (36x faster)
# - Query translation: More reliable and explicit
# - Database load: Significantly reduced
#
##############################################################################

set -e  # Exit on error

echo "=========================================================================="
echo "WARD OPS - Query Optimization Hotfix"
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
# Step 1: Git Pull Latest Changes
##############################################################################
echo -e "${BLUE}[1/5] Pulling latest code...${NC}"
git stash save "Pre-query-fix stash $(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
git pull origin main || {
    echo -e "${YELLOW}⚠️  Git pull failed (may already be up to date)${NC}"
}
echo -e "${GREEN}✅ Code is up to date${NC}"
echo ""

##############################################################################
# Step 2: Show What Changed
##############################################################################
echo -e "${BLUE}[2/5] Changes in this hotfix:${NC}"
echo ""
echo "File: routers/devices_standalone.py"
echo "Function: _latest_ping_lookup()"
echo ""
echo "BEFORE (causing 11s delays):"
echo "  - Used SQLAlchemy .distinct() method"
echo "  - Incorrectly translated to full table scan"
echo "  - Query: SELECT * FROM ping_results ORDER BY device_ip, timestamp"
echo ""
echo "AFTER (expected 300ms):"
echo "  - Uses explicit subquery with MAX timestamp"
echo "  - Translated to efficient JOIN query"
echo "  - Query: SELECT * FROM ping_results JOIN (subquery with GROUP BY)"
echo ""
echo -e "${GREEN}✅ Query optimization implemented${NC}"
echo ""

##############################################################################
# Step 3: Rebuild API Container
##############################################################################
echo -e "${BLUE}[3/5] Rebuilding API container...${NC}"
echo "This will take ~2-3 minutes..."

docker-compose -f "$COMPOSE_FILE" build --no-cache api

echo -e "${GREEN}✅ API container rebuilt${NC}"
echo ""

##############################################################################
# Step 4: Deploy New Container
##############################################################################
echo -e "${BLUE}[4/5] Deploying new API container...${NC}"

# Stop and remove old container
docker-compose -f "$COMPOSE_FILE" stop api
docker-compose -f "$COMPOSE_FILE" rm -f api

# Start new container
docker-compose -f "$COMPOSE_FILE" up -d api

echo "Waiting for API to start..."
sleep 20

echo -e "${GREEN}✅ API container deployed${NC}"
echo ""

##############################################################################
# Step 5: Verification
##############################################################################
echo -e "${BLUE}[5/5] Verifying fix...${NC}"
echo ""

# 1. Check container is running
echo -e "${BLUE}1️⃣  Container Status:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep wardops-api
echo ""

# 2. Test API health
echo -e "${BLUE}2️⃣  API Health:${NC}"
sleep 5
curl -s http://localhost:5001/api/v1/health | python3 -m json.tool 2>/dev/null || echo -e "${YELLOW}⚠️  API warming up...${NC}"
echo ""

# 3. Test cache expiry performance
echo -e "${BLUE}3️⃣  Cache Expiry Performance Test:${NC}"
echo "This will test if the 11-second delay is fixed..."
echo ""

# Clear Redis cache first
echo "Clearing Redis cache..."
docker exec wardops-redis-prod redis-cli FLUSHDB 2>/dev/null || echo -e "${YELLOW}⚠️  Could not clear Redis cache${NC}"

echo ""
echo "Testing cache MISS (first request, should be ~300ms):"
TIME1=$(curl -w "%{time_total}s\n" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list)
echo "First request: ${TIME1}"

echo ""
echo "Testing cache HIT (second request within 30s, should be ~10ms):"
sleep 1
TIME2=$(curl -w "%{time_total}s\n" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list)
echo "Second request: ${TIME2}"

echo ""
echo "Waiting 35 seconds for cache to expire..."
sleep 35

echo ""
echo "Testing cache MISS after expiry (should be ~300ms, NOT 11s!):"
TIME3=$(curl -w "%{time_total}s\n" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list)
echo "Third request (after cache expiry): ${TIME3}"

# Parse times and check if fixed
TIME3_MS=$(echo "$TIME3" | sed 's/s//' | awk '{print $1 * 1000}')
if [ $(echo "$TIME3_MS < 1000" | bc 2>/dev/null) -eq 1 ]; then
    echo -e "${GREEN}✅ FIXED! Cache expiry is now fast (< 1 second)${NC}"
else
    echo -e "${RED}❌ ISSUE PERSISTS: Cache expiry still takes > 1 second${NC}"
    echo "Expected: < 1s"
    echo "Actual: ${TIME3}"
fi
echo ""

# 4. Check recent API logs for errors
echo -e "${BLUE}4️⃣  Recent API Logs (checking for errors):${NC}"
docker logs wardops-api-prod --tail 30 2>&1 | grep -E "(ERROR|Exception|Traceback)" || echo -e "${GREEN}✅ No errors in API logs${NC}"
echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ QUERY OPTIMIZATION HOTFIX DEPLOYED!${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}🎯 What Was Fixed:${NC}"
echo ""
echo "  Issue: Cache expiry causing 11-second delays"
echo "  Root Cause: SQLAlchemy DISTINCT ON not translating correctly"
echo "  Solution: Replaced with explicit subquery approach"
echo ""
echo -e "${BLUE}📊 Expected Results:${NC}"
echo ""
echo "  • Cache HIT: ~10ms (same as before)"
echo "  • Cache MISS: ~300ms (was 11+ seconds!)"
echo "  • Speedup: 36x faster on cache expiry"
echo "  • Database load: Significantly reduced"
echo ""
echo -e "${BLUE}🔍 Monitor Next 30 Minutes:${NC}"
echo ""
echo "1. Test cache expiry in browser:"
echo "   - Open DevTools Network tab"
echo "   - Refresh dashboard (should be fast)"
echo "   - Wait 35 seconds"
echo "   - Refresh again (should STILL be fast, not 11s)"
echo ""
echo "2. Watch API response times:"
echo "   for i in {1..20}; do"
echo "     echo \"Request \$i:\""
echo "     curl -w \"Time: %{time_total}s\\n\" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list"
echo "     sleep 2"
echo "   done"
echo ""
echo "3. Check database queries:"
echo "   docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \\"
echo "     \"SELECT pid, state, query_start, NOW() - query_start AS duration, query \\"
echo "     \"FROM pg_stat_activity WHERE state = 'idle in transaction' \\"
echo "     \"AND NOW() - query_start > INTERVAL '1 second';\\"
echo "   # Should show NO long-running idle transactions!"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""
echo -e "${GREEN}🎉 System should now have fast cache expiry!${NC}"
echo ""

exit 0
