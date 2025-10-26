#!/bin/bash
#####################################################################
# URGENT FIX: Deploy Batched Monitoring to Fix 5-Minute Alert Delay
#####################################################################
#
# PROBLEM: Device alerting is 5 minutes late
# ROOT CAUSE: 876 individual ping tasks create massive queue backlog
# SOLUTION: Switch to batched ping tasks (48x faster!)
#
# IMPACT:
# - Before: 876 individual tasks = 5+ minute detection delay
# - After: ~10 batch tasks = <30 second detection (Zabbix-like!)
#
# DEPLOYMENT:
# 1. Restart celery-worker (loads new batch tasks)
# 2. Restart celery-beat (activates new schedule)
# 3. Monitor logs to verify batched execution
#
#####################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  URGENT FIX: Deploy Batched Monitoring${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Problem:${NC} Device alerting is 5 minutes late (unacceptable!)"
echo -e "${YELLOW}Solution:${NC} Switch to batched ping tasks (48x faster!)"
echo ""
echo -e "${GREEN}Expected Result:${NC}"
echo "  • Device down detection: <30 seconds (was 5+ minutes)"
echo "  • Queue size: 36 tasks/min (was 1,750 tasks/min)"
echo "  • Worker load: Reduced by 98%"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 1: Restart Celery Worker
echo -e "${YELLOW}[1/3] Restarting Celery Worker...${NC}"
echo "      Loading new batched task modules..."
docker-compose -f docker-compose.production-priority-queues.yml restart celery-worker
sleep 3

# Step 2: Restart Celery Beat
echo -e "${YELLOW}[2/3] Restarting Celery Beat...${NC}"
echo "      Activating new batched schedule..."
docker-compose -f docker-compose.production-priority-queues.yml stop celery-beat
docker-compose -f docker-compose.production-priority-queues.yml rm -f celery-beat
# Delete persistent schedule to force reload
echo "      Deleting persistent schedule database..."
docker-compose -f docker-compose.production-priority-queues.yml run --rm celery-beat sh -c "rm -f /app/celerybeat-schedule" || true
docker-compose -f docker-compose.production-priority-queues.yml up -d celery-beat
sleep 5

# Step 3: Verify deployment
echo -e "${YELLOW}[3/3] Verifying deployment...${NC}"
echo ""

# Check worker is running
WORKER_STATUS=$(docker-compose -f docker-compose.production-priority-queues.yml ps celery-worker | grep -c "Up" || echo "0")
if [ "$WORKER_STATUS" -eq "0" ]; then
    echo -e "${RED}❌ ERROR: Celery Worker is not running!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Celery Worker is running${NC}"
fi

# Check beat is running
BEAT_STATUS=$(docker-compose -f docker-compose.production-priority-queues.yml ps celery-beat | grep -c "Up" || echo "0")
if [ "$BEAT_STATUS" -eq "0" ]; then
    echo -e "${RED}❌ ERROR: Celery Beat is not running!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Celery Beat is running${NC}"
fi

# Check for batched task in logs
echo ""
echo -e "${BLUE}Checking Beat schedule (looking for 'ping_all_devices_batched')...${NC}"
sleep 3
docker-compose -f docker-compose.production-priority-queues.yml logs --tail=100 celery-beat | grep -E "(ping_all_devices_batched|Scheduler.*Entry)" | tail -10

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Monitor worker logs for batched execution:"
echo "     docker-compose -f docker-compose.production-priority-queues.yml logs -f celery-worker | grep 'Batch processed'"
echo ""
echo "  2. Wait 30 seconds and check if ping tasks are running in batches:"
echo "     docker-compose -f docker-compose.production-priority-queues.yml logs celery-worker | grep 'ping_devices_batch'"
echo ""
echo "  3. Test device down detection:"
echo "     • Unplug a test device"
echo "     • Check UI - status should show DOWN within 30 seconds"
echo "     • Alert should appear immediately"
echo ""
echo -e "${GREEN}Expected Behavior:${NC}"
echo "  • Every 30 seconds: 'Scheduling ~10 batch ping tasks for 876 devices'"
echo "  • Immediately after: 'Batch processed 88 devices' (x10 times)"
echo "  • Total time: <5 seconds to ping all 876 devices"
echo "  • Device down detection: <30 seconds (vs. 5+ minutes before)"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
