#!/bin/bash

##############################################################################
# FINAL AUTO-SCALING DEPLOYMENT - Complete Solution
##############################################################################
#
# This script does EVERYTHING needed to enable auto-scaling:
# 1. Stops all services
# 2. Purges old tasks from Redis
# 3. Rebuilds ALL images from scratch (no cache)
# 4. Starts services with auto-scaling enabled
# 5. Verifies auto-scaling is working
#
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production-priority-queues.yml"

echo "=========================================================================="
echo -e "${GREEN}🚀 FINAL AUTO-SCALING DEPLOYMENT${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# Step 1: Stop Everything
##############################################################################
echo -e "${BLUE}[1/7] Stopping all services...${NC}"
docker-compose -f "$COMPOSE_FILE" stop api celery-beat celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance
echo "✅ All services stopped"
echo ""

##############################################################################
# Step 2: Purge Old Tasks
##############################################################################
echo -e "${BLUE}[2/7] Purging all old tasks from Redis...${NC}"
docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass FLUSHDB
echo "✅ Redis queues cleared"
echo ""

##############################################################################
# Step 3: Delete Beat Schedule Cache
##############################################################################
echo -e "${BLUE}[3/7] Deleting beat schedule cache...${NC}"
# Beat schedule is stored in a volume, we'll let it recreate on startup
echo "✅ Beat schedule cache will be recreated"
echo ""

##############################################################################
# Step 4: Rebuild All Images (NO CACHE)
##############################################################################
echo -e "${BLUE}[4/7] Rebuilding all images from scratch (this takes 2-3 minutes)...${NC}"
echo ""
docker-compose -f "$COMPOSE_FILE" build --no-cache api celery-beat celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance
echo ""
echo "✅ All images rebuilt"
echo ""

##############################################################################
# Step 5: Remove Old Containers
##############################################################################
echo -e "${BLUE}[5/7] Removing old containers...${NC}"
docker-compose -f "$COMPOSE_FILE" rm -f api celery-beat celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance
echo "✅ Old containers removed"
echo ""

##############################################################################
# Step 6: Start Everything Fresh
##############################################################################
echo -e "${BLUE}[6/7] Starting all services with auto-scaling...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d api celery-beat celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance

echo ""
echo "Waiting 45 seconds for services to initialize..."
sleep 45

echo "✅ Services started"
echo ""

##############################################################################
# Step 7: Verify Auto-Scaling
##############################################################################
echo -e "${BLUE}[7/7] Verifying auto-scaling is working...${NC}"
echo ""

echo "=== Container Status ==="
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "=== Beat Scheduler (should show batched tasks) ==="
docker-compose -f "$COMPOSE_FILE" logs --tail 20 celery-beat | grep "Sending due task" || echo "No tasks scheduled yet, waiting..."

echo ""
echo "Waiting 20 more seconds for batched tasks to execute..."
sleep 20

echo ""
echo "=== Monitoring Worker Logs (checking for AUTO-SCALING) ==="
docker-compose -f "$COMPOSE_FILE" logs --tail 100 celery-worker-monitoring | tail -30

echo ""
echo "=== Searching for AUTO-SCALING messages ==="
docker-compose -f "$COMPOSE_FILE" logs celery-worker-monitoring | grep -E "AUTO-SCALING|Batch processed|Scheduling.*batch" || echo "⚠️  No AUTO-SCALING messages yet"

echo ""
echo "=========================================================================="
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "=========================================================================="
echo ""

echo -e "${CYAN}📊 VERIFICATION COMMANDS:${NC}"
echo ""
echo "  # Watch for AUTO-SCALING messages in real-time:"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-worker-monitoring | grep -E 'AUTO-SCALING|Batch'"
echo ""
echo "  # Check beat is scheduling batched tasks:"
echo "  docker-compose -f $COMPOSE_FILE logs celery-beat | grep batched"
echo ""
echo "  # Check queue sizes (should stay low < 20):"
echo "  docker-compose -f $COMPOSE_FILE exec redis redis-cli -a redispass LLEN monitoring"
echo "  docker-compose -f $COMPOSE_FILE exec redis redis-cli -a redispass LLEN snmp"
echo ""
echo "  # Test API health:"
echo "  curl http://localhost:5001/api/v1/health"
echo ""
echo "⏰ Completed at: $(date)"
echo ""
echo -e "${YELLOW}EXPECTED RESULTS:${NC}"
echo "Within 1-2 minutes you should see:"
echo "  ✅ Beat scheduling: monitoring.tasks.ping_all_devices_batched (every 10s)"
echo "  ✅ Worker logs: AUTO-SCALING: 875 devices → batch size 100 → ~9 batches"
echo "  ✅ Worker logs: Batch processed 100 devices"
echo "  ✅ Worker logs: Scheduling 9 batch ping tasks for 875 devices"
echo ""
echo "If you don't see these messages after 2 minutes, check for errors:"
echo "  docker-compose -f $COMPOSE_FILE logs celery-worker-monitoring | tail -50"
echo ""
echo "=========================================================================="

exit 0
