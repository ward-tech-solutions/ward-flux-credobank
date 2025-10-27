#!/bin/bash

##############################################################################
# WARD OPS - Real-Time Status Diagnostic Script
##############################################################################
#
# Purpose: Diagnose why devices show UP when they're actually DOWN
# Issue: 3-6 minute delay in status updates
#
##############################################################################

set -e

echo "=========================================================================="
echo "WARD OPS - Real-Time Status Diagnostic"
echo "=========================================================================="
echo ""
echo "⏰ Current time: $(date)"
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
# 1. Check Celery Workers
##############################################################################
echo -e "${BLUE}[1/7] Checking Celery Workers...${NC}"
echo ""

# Check if celery-worker container is running
echo "Celery Worker Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "worker.*prod" || echo -e "${RED}❌ Celery worker not running!${NC}"

echo ""
echo "Celery Beat Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "beat.*prod" || echo -e "${RED}❌ Celery beat not running!${NC}"

echo ""
echo "Active Celery Workers:"
docker exec wardops-worker-prod celery -A celery_app inspect active 2>/dev/null || echo -e "${YELLOW}⚠️  Could not inspect celery workers${NC}"

echo ""
echo "Celery Queue Status:"
docker exec wardops-worker-prod celery -A celery_app inspect stats 2>/dev/null | grep -E "total|pool" || echo -e "${YELLOW}⚠️  Could not get celery stats${NC}"

echo ""
echo -e "${GREEN}✅ Section 1 complete${NC}"
echo ""

##############################################################################
# 2. Check Ping Task Schedule
##############################################################################
echo -e "${BLUE}[2/7] Checking Ping Task Schedule...${NC}"
echo ""

echo "Scheduled tasks (beat_schedule):"
docker exec wardops-beat-prod celery -A celery_app inspect scheduled 2>/dev/null | grep -A 5 "ping_all_devices" || echo -e "${YELLOW}⚠️  Could not get scheduled tasks${NC}"

echo ""
echo "Recent celery logs (ping tasks):"
docker logs wardops-worker-prod --tail 50 2>&1 | grep -i "ping" | tail -20 || echo "No recent ping tasks found"

echo ""
echo -e "${GREEN}✅ Section 2 complete${NC}"
echo ""

##############################################################################
# 3. Check Latest Ping Results for Kharagauli Devices
##############################################################################
echo -e "${BLUE}[3/7] Checking Latest Ping Results (Kharagauli devices)...${NC}"
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    device_name,
    device_ip,
    is_reachable,
    timestamp,
    NOW() - timestamp AS age,
    avg_rtt_ms
FROM ping_results
WHERE device_name ILIKE '%Kharagauli%'
ORDER BY timestamp DESC
LIMIT 10;
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not query ping results${NC}"

echo ""
echo -e "${GREEN}✅ Section 3 complete${NC}"
echo ""

##############################################################################
# 4. Check Device down_since Timestamps
##############################################################################
echo -e "${BLUE}[4/7] Checking down_since timestamps...${NC}"
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    name,
    ip,
    down_since,
    CASE
        WHEN down_since IS NOT NULL THEN NOW() - down_since
        ELSE NULL
    END AS downtime_duration,
    enabled
FROM standalone_devices
WHERE name ILIKE '%Kharagauli%'
ORDER BY name;
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not query devices${NC}"

echo ""
echo -e "${GREEN}✅ Section 4 complete${NC}"
echo ""

##############################################################################
# 5. Check Redis Cache
##############################################################################
echo -e "${BLUE}[5/7] Checking Redis Cache...${NC}"
echo ""

echo "Redis keys (device list cache):"
docker exec wardops-redis-prod redis-cli KEYS "devices:list:*" 2>/dev/null | head -10 || echo -e "${YELLOW}⚠️  Could not check Redis${NC}"

echo ""
echo "Sample cached device list:"
CACHE_KEY=$(docker exec wardops-redis-prod redis-cli KEYS "devices:list:*" 2>/dev/null | head -1)
if [ ! -z "$CACHE_KEY" ]; then
    echo "Cache key: $CACHE_KEY"
    TTL=$(docker exec wardops-redis-prod redis-cli TTL "$CACHE_KEY" 2>/dev/null)
    echo "TTL: ${TTL} seconds"
    echo ""
    echo "First device in cache:"
    docker exec wardops-redis-prod redis-cli GET "$CACHE_KEY" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list) and len(data) > 0:
        device = data[0]
        print(f\"Name: {device.get('name', 'N/A')}\")
        print(f\"IP: {device.get('ip', 'N/A')}\")
        print(f\"Status: {device.get('ping_status', 'N/A')}\")
        print(f\"Down Since: {device.get('down_since', 'N/A')}\")
except:
    print('Could not parse cache data')
" || echo "Could not parse cached data"
else
    echo -e "${YELLOW}⚠️  No device list cache found${NC}"
fi

echo ""
echo -e "${GREEN}✅ Section 5 complete${NC}"
echo ""

##############################################################################
# 6. Check Recent Alert History
##############################################################################
echo -e "${BLUE}[6/7] Checking Recent Alerts (last 10 minutes)...${NC}"
echo ""

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    ah.triggered_at,
    sd.name AS device_name,
    sd.ip,
    ah.severity,
    ah.message,
    ah.resolved_at,
    CASE
        WHEN ah.resolved_at IS NULL THEN 'ACTIVE'
        ELSE 'RESOLVED'
    END AS status
FROM alert_history ah
JOIN standalone_devices sd ON ah.device_id = sd.id
WHERE ah.triggered_at > NOW() - INTERVAL '10 minutes'
ORDER BY ah.triggered_at DESC
LIMIT 20;
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not query alerts${NC}"

echo ""
echo -e "${GREEN}✅ Section 6 complete${NC}"
echo ""

##############################################################################
# 7. Test Real-Time Ping
##############################################################################
echo -e "${BLUE}[7/7] Testing Real-Time Ping for Kharagauli Devices...${NC}"
echo ""

echo "Pinging Kharagauli-ATM (10.199.78.163):"
ping -c 2 -W 1 10.199.78.163 2>&1 | tail -5 || echo -e "${RED}❌ PING FAILED${NC}"

echo ""
echo "Pinging Kharagauli-AP (10.195.78.252):"
ping -c 2 -W 1 10.195.78.252 2>&1 | tail -5 || echo -e "${RED}❌ PING FAILED${NC}"

echo ""
echo "Pinging Kharagauli-NVR (10.199.78.140):"
ping -c 2 -W 1 10.199.78.140 2>&1 | tail -5 || echo -e "${RED}❌ PING FAILED${NC}"

echo ""
echo -e "${GREEN}✅ Section 7 complete${NC}"
echo ""

##############################################################################
# Summary & Recommendations
##############################################################################
echo "=========================================================================="
echo -e "${BLUE}📊 DIAGNOSTIC SUMMARY${NC}"
echo "=========================================================================="
echo ""

echo "Issues to check:"
echo ""
echo "1. ⏰ Celery workers running?"
echo "   - Check section 1 output above"
echo "   - Should see: wardops-celery-worker (Up)"
echo "   - Should see: wardops-celery-beat (Up)"
echo ""
echo "2. 📅 Ping tasks being scheduled?"
echo "   - Check section 2 output above"
echo "   - Should see: ping_all_devices running every 30 seconds"
echo "   - Should see recent ping logs"
echo ""
echo "3. 💾 Latest ping results fresh?"
echo "   - Check section 3 output above"
echo "   - Age should be < 1 minute"
echo "   - is_reachable should match actual status"
echo ""
echo "4. 🔴 down_since timestamps set?"
echo "   - Check section 4 output above"
echo "   - DOWN devices should have down_since set"
echo "   - UP devices should have down_since = NULL"
echo ""
echo "5. 📦 Redis cache up-to-date?"
echo "   - Check section 5 output above"
echo "   - TTL should be 0-30 seconds"
echo "   - Cache should reflect latest ping results"
echo ""
echo "6. 🚨 Alerts being created?"
echo "   - Check section 6 output above"
echo "   - DOWN devices should have ACTIVE alerts"
echo "   - Recent alerts should be visible"
echo ""
echo "7. 🏓 Actual ping working?"
echo "   - Check section 7 output above"
echo "   - Compare with database ping results"
echo ""
echo "=========================================================================="
echo "Possible root causes:"
echo ""
echo "❌ IF Celery workers not running:"
echo "   → Start: docker-compose -f $COMPOSE_FILE up -d celery-worker celery-beat"
echo ""
echo "❌ IF Ping results are stale (age > 1 minute):"
echo "   → Celery worker is stuck or overloaded"
echo "   → Check logs: docker logs wardops-celery-worker --tail 100"
echo ""
echo "❌ IF down_since not set but device is DOWN:"
echo "   → Ping task logic issue"
echo "   → Check task code in monitoring/tasks.py:178-328"
echo ""
echo "❌ IF Redis cache is stale:"
echo "   → Clear cache: docker exec wardops-redis-prod redis-cli FLUSHDB"
echo "   → Frontend will fetch fresh data"
echo ""
echo "❌ IF alerts not being created:"
echo "   → Alert creation logic issue"
echo "   → Check task code lines 264-279"
echo ""
echo "=========================================================================="
echo ""
echo "⏰ Diagnostic completed at: $(date)"
echo ""

exit 0
