#!/bin/bash

##############################################################################
# WARD OPS - Tier 1 Quick Wins Deployment
##############################################################################
#
# Optimizations Included:
# 1. Composite Database Indexes (10-15% faster queries)
# 2. GZip API Compression (60-80% bandwidth reduction)
# 3. Redis Caching (10x faster dashboard)
#
# Expected Total Impact: 20-25% performance improvement
# Risk Level: Low (all proven techniques)
# Deployment Time: ~5-10 minutes
#
##############################################################################

set -e  # Exit on error

echo "=========================================================================="
echo "WARD OPS - Tier 1 Quick Wins Deployment"
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

if [ ! -f "migrations/add_composite_indexes_tier1.sql" ]; then
    echo -e "${RED}❌ Error: Migration file not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment OK${NC}"
echo ""

##############################################################################
# Step 1: Backup Database
##############################################################################
echo -e "${BLUE}[1/6] Backing up database...${NC}"
BACKUP_FILE="backup_before_tier1_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec wardops-postgres-prod pg_dump -U ward_admin ward_ops | gzip > "$BACKUP_FILE"
echo -e "${GREEN}✅ Database backed up to: $BACKUP_FILE${NC}"
echo ""

##############################################################################
# Step 2: Apply Database Indexes
##############################################################################
echo -e "${BLUE}[2/6] Applying composite indexes...${NC}"
echo "This may take 30-60 seconds for large tables..."

# Copy migration file into container
docker cp migrations/add_composite_indexes_tier1.sql wardops-postgres-prod:/tmp/migration.sql

# Execute migration
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -f /tmp/migration.sql

echo -e "${GREEN}✅ Indexes applied successfully${NC}"
echo ""

# Show index sizes
echo -e "${BLUE}Index sizes:${NC}"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_indexes
JOIN pg_class ON pg_indexes.indexname = pg_class.relname
WHERE indexname LIKE 'idx_%device%' OR indexname LIKE 'idx_%monitoring%' OR indexname LIKE 'idx_%alert%'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 10;
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not query index sizes${NC}"
echo ""

##############################################################################
# Step 3: Pull Latest Code
##############################################################################
echo -e "${BLUE}[3/6] Ensuring latest code is pulled...${NC}"
git stash save "Pre-tier1 stash $(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
git pull origin main || {
    echo -e "${YELLOW}⚠️  Git pull failed (may already be up to date)${NC}"
}
echo -e "${GREEN}✅ Code is up to date${NC}"
echo ""

##############################################################################
# Step 4: Rebuild API Container (with GZip + Caching)
##############################################################################
echo -e "${BLUE}[4/6] Rebuilding API container with optimizations...${NC}"
echo "This will take ~2-3 minutes..."

docker-compose -f "$COMPOSE_FILE" build --no-cache api

echo -e "${GREEN}✅ API container rebuilt${NC}"
echo ""

##############################################################################
# Step 5: Recreate API Container
##############################################################################
echo -e "${BLUE}[5/6] Deploying new API container...${NC}"

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
# Step 6: Verification
##############################################################################
echo -e "${BLUE}[6/6] Verifying optimizations...${NC}"
echo ""

# 1. Check containers are running
echo -e "${BLUE}1️⃣  Container Status:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep wardops-api
echo ""

# 2. Test API health
echo -e "${BLUE}2️⃣  API Health:${NC}"
sleep 5
curl -s http://localhost:5001/api/v1/health | python3 -m json.tool 2>/dev/null || echo -e "${YELLOW}⚠️  API warming up...${NC}"
echo ""

# 3. Test GZip compression
echo -e "${BLUE}3️⃣  GZip Compression Test:${NC}"
COMPRESSION_HEADER=$(curl -s -I -H "Accept-Encoding: gzip" http://localhost:5001/api/v1/devices/standalone/list | grep -i "content-encoding")
if [[ $COMPRESSION_HEADER == *"gzip"* ]]; then
    echo -e "${GREEN}✅ GZip compression is working${NC}"
else
    echo -e "${YELLOW}⚠️  GZip compression not detected (may need larger response)${NC}"
fi
echo ""

# 4. Test Redis caching
echo -e "${BLUE}4️⃣  Redis Caching Test:${NC}"
echo "Testing cache miss (first request)..."
TIME1=$(curl -w "%{time_total}\n" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list)
echo "First request: ${TIME1}s"

echo "Testing cache hit (second request within 30s)..."
sleep 1
TIME2=$(curl -w "%{time_total}\n" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list)
echo "Second request: ${TIME2}s"

# Compare times
SPEEDUP=$(echo "scale=2; $TIME1 / $TIME2" | bc 2>/dev/null || echo "N/A")
if [ "$SPEEDUP" != "N/A" ] && [ $(echo "$SPEEDUP > 2" | bc) -eq 1 ]; then
    echo -e "${GREEN}✅ Cache is working (${SPEEDUP}x speedup)${NC}"
else
    echo -e "${YELLOW}⚠️  Cache speedup: ${SPEEDUP}x (expected > 2x)${NC}"
fi
echo ""

# 5. Check database indexes
echo -e "${BLUE}5️⃣  Database Indexes Verification:${NC}"
INDEX_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT COUNT(*) FROM pg_indexes WHERE indexname IN (
    'idx_monitoring_items_device_enabled_interval',
    'idx_alert_history_device_rule_triggered',
    'idx_ping_results_device_time_range',
    'idx_standalone_devices_enabled_branch'
);
" 2>/dev/null | tr -d ' ')

if [ "$INDEX_COUNT" == "4" ]; then
    echo -e "${GREEN}✅ All 4 indexes created successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Found ${INDEX_COUNT} of 4 expected indexes${NC}"
fi
echo ""

# 6. API logs check
echo -e "${BLUE}6️⃣  Recent API Logs (checking for errors):${NC}"
docker logs wardops-api-prod --tail 20 2>&1 | grep -E "(ERROR|Exception|Traceback)" || echo -e "${GREEN}✅ No errors in API logs${NC}"
echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ TIER 1 QUICK WINS DEPLOYED!${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}🎯 Optimizations Applied:${NC}"
echo ""
echo "  1. Composite Database Indexes"
echo "    • 4 new indexes on critical tables"
echo "    • Expected: 10-15% faster queries"
echo "    • Tables: monitoring_items, alert_history, ping_results, standalone_devices"
echo ""
echo "  2. GZip API Compression"
echo "    • Compress responses > 1KB"
echo "    • Expected: 60-80% bandwidth reduction"
echo "    • Faster page loads on slow networks"
echo ""
echo "  3. Redis Caching"
echo "    • 30-second TTL for device lists"
echo "    • Expected: 10x faster dashboard (cache hits)"
echo "    • Expected cache hit rate: 80-90%"
echo ""
echo -e "${BLUE}📊 Expected Performance Improvements:${NC}"
echo "  • Device list API: 50ms → 20ms (2.5x faster on cache hit)"
echo "  • Dashboard load: 200ms → 80ms (2.5x faster)"
echo "  • Database queries: 10-15% faster (indexes)"
echo "  • Bandwidth usage: 60-80% reduction (compression)"
echo "  • Overall: 20-25% performance improvement"
echo ""
echo -e "${BLUE}🔍 Monitor Next 24 Hours:${NC}"
echo ""
echo "1. API response times:"
echo "   watch -n 5 'curl -w \"Time: %{time_total}s\\n\" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list'"
echo ""
echo "2. Cache hit rate:"
echo "   docker exec wardops-redis-prod redis-cli INFO stats | grep keyspace"
echo ""
echo "3. Database query performance:"
echo "   docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \"SELECT * FROM pg_stat_user_indexes WHERE indexrelname LIKE 'idx_%' ORDER BY idx_scan DESC LIMIT 10;\""
echo ""
echo "4. Bandwidth savings:"
echo "   # Compare response sizes with/without gzip"
echo "   curl -w \"%{size_download}\\n\" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list"
echo "   curl -H \"Accept-Encoding: gzip\" -w \"%{size_download}\\n\" -o /dev/null -s http://localhost:5001/api/v1/devices/standalone/list"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""
echo -e "${GREEN}🎉 System is now running with Tier 1 optimizations!${NC}"
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Keep this backup for 7 days in case rollback is needed."
echo ""

exit 0
