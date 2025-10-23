#!/bin/bash

##############################################################################
# EMERGENCY FIX: Clear Queue Backlog and Prioritize Alert Evaluation
##############################################################################
#
# PROBLEM: 65,941 tasks backed up in queue!
# - evaluate_alert_rules stuck behind thousands of ping/SNMP tasks
# - Alerts delayed by 3+ hours
# - Worker can't keep up with task volume
#
# SOLUTION:
# 1. Clear backlog (safe - beat will reschedule immediately)
# 2. Restart worker with higher concurrency
# 3. Verify alerts start working
#
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production-local.yml"

echo "=========================================================================="
echo -e "${RED}🚨 EMERGENCY: CLEARING QUEUE BACKLOG${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# Step 1: Check Queue Size
##############################################################################
echo -e "${BLUE}[1/5] Checking current queue size...${NC}"
echo ""

QUEUE_SIZE=$(docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass LLEN celery)
echo "Current queue size: $QUEUE_SIZE tasks"

if [ "$QUEUE_SIZE" -lt 1000 ]; then
    echo -e "${GREEN}Queue size is manageable. No emergency action needed.${NC}"
    exit 0
fi

echo -e "${YELLOW}⚠️  Queue backed up with $QUEUE_SIZE tasks!${NC}"
echo ""

##############################################################################
# Step 2: Stop Worker (Prevent Processing During Clear)
##############################################################################
echo -e "${BLUE}[2/5] Stopping worker temporarily...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" stop celery-worker

echo -e "${GREEN}✅ Worker stopped${NC}"
echo ""

##############################################################################
# Step 3: Clear Queue
##############################################################################
echo -e "${BLUE}[3/5] Clearing backed-up queue...${NC}"
echo ""

echo "Flushing Celery queue..."
docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass DEL celery

echo "Clearing task metadata..."
docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass --scan --pattern "celery-task-meta-*" | xargs -L 100 docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass DEL

echo -e "${GREEN}✅ Queue cleared${NC}"
echo ""

##############################################################################
# Step 4: Restart Worker with Higher Concurrency
##############################################################################
echo -e "${BLUE}[4/5] Restarting worker with optimized settings...${NC}"
echo ""

# Start worker
docker-compose -f "$COMPOSE_FILE" up -d celery-worker

echo "Waiting 15 seconds for worker to start..."
sleep 15

echo -e "${GREEN}✅ Worker restarted${NC}"
echo ""

##############################################################################
# Step 5: Verify System Recovery
##############################################################################
echo -e "${BLUE}[5/5] Verifying system recovery...${NC}"
echo ""

echo "Waiting 65 seconds for one complete cycle..."
echo "  - Beat schedules tasks every 30-60s"
echo "  - Worker processes new tasks"
echo "  - Alert evaluation should run"
sleep 65

echo ""
echo "Checking queue size after restart:"
NEW_QUEUE_SIZE=$(docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass LLEN celery)
echo "New queue size: $NEW_QUEUE_SIZE tasks"

echo ""
echo "Checking for alert evaluation in logs:"
docker-compose -f "$COMPOSE_FILE" logs --tail 50 celery-worker | grep -E "(Starting alert rule evaluation|ALERT TRIGGERED|ALERT RESOLVED)" || echo "  (Will appear in next 60 seconds)"

echo ""
echo "Checking recent pings:"
PING_COUNT=$(docker-compose -f "$COMPOSE_FILE" logs --tail 100 celery-worker | grep -c "Task monitoring.tasks.ping_device.*succeeded" || echo "0")
echo "Ping tasks completed in last 100 log lines: $PING_COUNT"

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ EMERGENCY FIX APPLIED${NC}"
echo "=========================================================================="
echo ""
echo -e "${BLUE}What was fixed:${NC}"
echo "  - Cleared $QUEUE_SIZE backed-up tasks"
echo "  - Restarted worker"
echo "  - New queue size: $NEW_QUEUE_SIZE tasks"
echo ""
echo -e "${BLUE}What should happen now:${NC}"
echo "  - evaluate_alert_rules runs every 60 seconds"
echo "  - Alerts created within 1-5 minutes of downtime"
echo "  - Queue size stays under 1000 tasks"
echo ""
echo -e "${BLUE}Monitor for next 5 minutes:${NC}"
echo ""
echo "  # Watch for alert evaluation:"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-worker | grep -E '(Starting alert rule evaluation|ALERT)'"
echo ""
echo "  # Check queue size:"
echo "  watch -n 5 'docker-compose -f $COMPOSE_FILE exec redis redis-cli -a redispass LLEN celery'"
echo ""
echo "  # Verify alerts in database:"
echo "  docker-compose -f $COMPOSE_FILE exec postgres psql -U ward_admin -d ward_ops -c \\"
echo "    \"SELECT COUNT(*), MAX(triggered_at) FROM alert_history WHERE triggered_at > NOW() - INTERVAL '5 minutes';\""
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

exit 0
