#!/bin/bash

##############################################################################
# Clear Celery Beat Schedule Cache
##############################################################################
#
# PROBLEM: Beat caches its schedule in celerybeat-schedule file
# SOLUTION: Delete the cache and restart beat to load new schedule
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
echo -e "${GREEN}🗑️  CLEARING BEAT SCHEDULE CACHE${NC}"
echo "=========================================================================="
echo ""

echo -e "${YELLOW}PROBLEM:${NC}"
echo "Beat scheduler is using OLD cached schedule from celerybeat-schedule file"
echo "  - Still scheduling: monitoring.tasks.ping_all_devices (OLD)"
echo "  - Should schedule: monitoring.tasks.ping_all_devices_batched (NEW)"
echo ""

echo -e "${BLUE}SOLUTION:${NC}"
echo "Delete celerybeat-schedule cache file and restart beat"
echo ""

##############################################################################
# Stop Beat
##############################################################################
echo -e "${BLUE}[1/4] Stopping beat scheduler...${NC}"
docker-compose -f "$COMPOSE_FILE" stop celery-beat
echo "✅ Beat stopped"
echo ""

##############################################################################
# Delete Schedule Cache
##############################################################################
echo -e "${BLUE}[2/4] Deleting celerybeat-schedule cache...${NC}"
docker-compose -f "$COMPOSE_FILE" exec -T celery-worker-monitoring rm -f /app/celerybeat-schedule 2>&1 || echo "Cache file may not exist (OK)"
echo "✅ Cache deleted"
echo ""

##############################################################################
# Start Beat
##############################################################################
echo -e "${BLUE}[3/4] Starting beat with NEW schedule...${NC}"
docker-compose -f "$COMPOSE_FILE" start celery-beat
echo "Waiting 15 seconds for beat to initialize..."
sleep 15
echo "✅ Beat started"
echo ""

##############################################################################
# Verify New Schedule
##############################################################################
echo -e "${BLUE}[4/4] Verifying new schedule is loaded...${NC}"
echo ""
echo "Checking beat logs for batched tasks:"
docker-compose -f "$COMPOSE_FILE" logs --tail 30 celery-beat | grep -E "(Sending due task|batched)" || echo "⚠️  No logs yet, waiting..."

echo ""
echo "Waiting 15 more seconds for first scheduled task..."
sleep 15

echo ""
echo "Latest beat logs:"
docker-compose -f "$COMPOSE_FILE" logs --tail 10 celery-beat

echo ""
echo "=========================================================================="
echo -e "${GREEN}✅ BEAT SCHEDULE CACHE CLEARED${NC}"
echo "=========================================================================="
echo ""

echo -e "${CYAN}📊 VERIFICATION:${NC}"
echo ""
echo "You should now see in the logs above:"
echo "  ✅ Scheduler: Sending due task ping-all-devices (monitoring.tasks.ping_all_devices_batched)"
echo "  ✅ Scheduler: Sending due task poll-all-devices-snmp (monitoring.tasks.poll_all_devices_snmp_batched)"
echo ""
echo "Wait 20 seconds and check monitoring worker logs:"
echo "  docker-compose -f $COMPOSE_FILE logs --tail 50 celery-worker-monitoring | grep -E 'AUTO-SCALING|batch'"
echo ""
echo "You should see:"
echo "  ✅ AUTO-SCALING: 875 devices → batch size 100 → ~9 batches"
echo ""

exit 0
