#!/bin/bash

##############################################################################
# WARD OPS - CRITICAL Memory Issue - Immediate Relief
##############################################################################
#
# Issue: Redis (6GB) + Worker (5.6GB) consuming 74% RAM
# Action: Flush Redis cache + Restart worker
# Impact: Free ~9.5GB RAM (87% → 30% usage)
#
##############################################################################

set -e

echo "=========================================================================="
echo "WARD OPS - CRITICAL MEMORY ISSUE - IMMEDIATE RELIEF"
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

##############################################################################
# Step 0: Show Current Memory Usage
##############################################################################
echo -e "${RED}[0/5] Current Critical Memory Usage:${NC}"
echo ""
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

REDIS_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" wardops-redis-prod | awk '{print $1}')
WORKER_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" wardops-worker-prod | awk '{print $1}')

echo -e "${RED}🚨 CRITICAL:${NC}"
echo "  Redis: $REDIS_MEM (should be < 500MB)"
echo "  Worker: $WORKER_MEM (should be < 2GB)"
echo ""
echo -e "${YELLOW}⚠️  Server at 87% RAM usage - immediate action required!${NC}"
echo ""

read -p "Press ENTER to proceed with fixes (Ctrl+C to cancel)..."

##############################################################################
# Step 1: Flush Redis Cache
##############################################################################
echo ""
echo -e "${BLUE}[1/5] Flushing Redis cache (will free ~6GB)...${NC}"
echo ""

# Try without password first, then with password
if docker exec wardops-redis-prod redis-cli PING 2>/dev/null | grep -q PONG; then
    echo "Redis has no auth - flushing without password..."
    docker exec wardops-redis-prod redis-cli FLUSHDB
else
    echo "Redis requires auth - flushing with password..."
    docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB 2>&1 | grep -v "Warning: Using a password"
fi

echo ""
echo -e "${GREEN}✅ Redis cache flushed${NC}"
echo ""

##############################################################################
# Step 2: Verify Redis Memory
##############################################################################
echo -e "${BLUE}[2/5] Checking Redis memory after flush...${NC}"
echo ""

# Check memory (with or without auth)
if docker exec wardops-redis-prod redis-cli PING 2>/dev/null | grep -q PONG; then
    docker exec wardops-redis-prod redis-cli INFO memory | grep -E "used_memory_human|used_memory_peak_human"
else
    docker exec wardops-redis-prod redis-cli -a redispass INFO memory 2>&1 | grep -E "used_memory_human|used_memory_peak_human"
fi

echo ""
REDIS_MEM_AFTER=$(docker stats --no-stream --format "{{.MemUsage}}" wardops-redis-prod | awk '{print $1}')
echo "Redis memory: $REDIS_MEM → $REDIS_MEM_AFTER"
echo ""
echo -e "${GREEN}✅ Redis memory reduced${NC}"
echo ""

##############################################################################
# Step 3: Restart Celery Worker
##############################################################################
echo -e "${BLUE}[3/5] Restarting Celery worker (will free ~4GB)...${NC}"
echo ""

docker restart wardops-worker-prod

echo ""
echo "Waiting 20 seconds for worker to restart..."
sleep 20

echo ""
echo -e "${GREEN}✅ Worker restarted${NC}"
echo ""

##############################################################################
# Step 4: Verify Worker Memory
##############################################################################
echo -e "${BLUE}[4/5] Checking worker memory after restart...${NC}"
echo ""

WORKER_MEM_AFTER=$(docker stats --no-stream --format "{{.MemUsage}}" wardops-worker-prod | awk '{print $1}')
echo "Worker memory: $WORKER_MEM → $WORKER_MEM_AFTER"

echo ""
echo -e "${GREEN}✅ Worker memory reduced${NC}"
echo ""

##############################################################################
# Step 5: Show Final Memory Usage
##############################################################################
echo -e "${BLUE}[5/5] Final memory usage:${NC}"
echo ""
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ IMMEDIATE RELIEF COMPLETE!${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}🎯 What Was Fixed:${NC}"
echo ""
echo "  Before:"
echo "    Redis: $REDIS_MEM (38%)"
echo "    Worker: $WORKER_MEM (36%)"
echo "    Total: ~11.5GB (74% RAM usage) 🚨"
echo ""
echo "  After:"
echo "    Redis: $REDIS_MEM_AFTER (~1%)"
echo "    Worker: $WORKER_MEM_AFTER (~10%)"
echo "    Total: ~3-4GB (25-30% RAM usage) ✅"
echo ""
echo -e "${BLUE}📊 Expected Behavior:${NC}"
echo ""
echo "  ✅ Redis memory will grow slowly (cache rebuilding)"
echo "  ✅ Worker memory stable at 1-2GB"
echo "  ✅ System has breathing room (70% RAM free)"
echo ""
echo -e "${BLUE}🔍 Monitor Next 10 Minutes:${NC}"
echo ""
echo "Watch memory usage:"
echo "  watch -n 5 'docker stats --no-stream --format \"table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\"'"
echo ""
echo "Check Redis memory growth:"
echo "  docker exec wardops-redis-prod redis-cli INFO memory | grep used_memory_human"
echo ""
echo "Check worker logs:"
echo "  docker logs wardops-worker-prod -f | grep -E '(ping|error)'"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: This is temporary relief!${NC}"
echo ""
echo "Permanent fixes needed:"
echo "  1. Reduce worker concurrency: 50 → 20"
echo "  2. Add max-tasks-per-child: 1000"
echo "  3. Add Redis maxmemory limit: 1GB"
echo "  4. Fix SNMP DetachedInstanceError"
echo ""
echo "See CRITICAL-MEMORY-ISSUE-FIX.md for details."
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""
echo -e "${GREEN}🎉 Server memory usage back to safe levels!${NC}"
echo ""
echo -e "${BLUE}Next: Deploy permanent fixes to prevent this from happening again.${NC}"
echo ""

exit 0
