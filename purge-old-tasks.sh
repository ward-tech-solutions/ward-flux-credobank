#!/bin/bash

##############################################################################
# Purge All Old Tasks and Start Fresh with Auto-Scaling
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
echo -e "${GREEN}🗑️  PURGING ALL OLD TASKS${NC}"
echo "=========================================================================="
echo ""

echo -e "${YELLOW}PROBLEM:${NC}"
echo "Thousands of OLD individual ping_device tasks still in queue"
echo "These were queued BEFORE we enabled auto-scaling batches"
echo ""

##############################################################################
# Stop All Workers
##############################################################################
echo -e "${BLUE}[1/5] Stopping all workers...${NC}"
docker-compose -f "$COMPOSE_FILE" stop celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance celery-beat
echo "✅ Workers stopped"
echo ""

##############################################################################
# Purge All Queues
##############################################################################
echo -e "${BLUE}[2/5] Purging all task queues...${NC}"
echo ""

echo "Flushing all queues from Redis..."
docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass FLUSHDB

echo "✅ All queues purged"
echo ""

##############################################################################
# Restart Workers
##############################################################################
echo -e "${BLUE}[3/5] Starting workers with clean queues...${NC}"
docker-compose -f "$COMPOSE_FILE" start celery-beat celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance

echo "Waiting 20 seconds for beat to start scheduling..."
sleep 20

echo "✅ Workers started"
echo ""

##############################################################################
# Verify Batched Tasks
##############################################################################
echo -e "${BLUE}[4/5] Verifying batched tasks are being scheduled...${NC}"
echo ""

echo "Beat scheduler logs:"
docker-compose -f "$COMPOSE_FILE" logs --tail 20 celery-beat | grep "Sending due task" || echo "No tasks scheduled yet"

echo ""
echo "Waiting 15 more seconds for batched tasks to execute..."
sleep 15

echo ""
echo -e "${BLUE}[5/5] Checking for AUTO-SCALING messages...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" logs --tail 100 celery-worker-monitoring | grep -E "AUTO-SCALING|ping_all_devices_batched|ping_devices_batch" || echo "⚠️  No AUTO-SCALING logs yet"

echo ""
echo "=========================================================================="
echo -e "${GREEN}✅ OLD TASKS PURGED${NC}"
echo "=========================================================================="
echo ""

echo -e "${CYAN}📊 MONITOR AUTO-SCALING:${NC}"
echo ""
echo "Watch for AUTO-SCALING messages:"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-worker-monitoring | grep -E 'AUTO-SCALING|batch'"
echo ""
echo "You should see within 1 minute:"
echo "  ✅ Task monitoring.tasks.ping_all_devices_batched received"
echo "  ✅ AUTO-SCALING: 875 devices → batch size 100 → ~9 batches"
echo "  ✅ Scheduling 9 batch ping tasks for 875 devices"
echo ""

exit 0
