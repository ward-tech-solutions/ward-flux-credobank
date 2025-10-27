#!/bin/bash

##############################################################################
# Restart Services with Auto-Scaling Configuration
##############################################################################
#
# WHAT THIS DOES:
# - Pulls latest celery_app.py with auto-scaling config
# - Rebuilds API and worker images
# - Restarts beat and workers to apply new configuration
# - Verifies auto-scaling is working
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
echo -e "${GREEN}🔄 RESTARTING WITH AUTO-SCALING CONFIGURATION${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# Pull Latest Code
##############################################################################
echo -e "${BLUE}[1/5] Pulling latest code from GitHub...${NC}"
echo ""

git pull origin main

echo "✅ Code updated"
echo ""

##############################################################################
# Rebuild Images
##############################################################################
echo -e "${BLUE}[2/5] Rebuilding images with new celery_app.py...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" build api celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance celery-beat

echo "✅ Images rebuilt"
echo ""

##############################################################################
# Restart Services
##############################################################################
echo -e "${BLUE}[3/5] Restarting services...${NC}"
echo ""

# Restart beat first (scheduler)
echo "Restarting beat scheduler..."
docker-compose -f "$COMPOSE_FILE" restart celery-beat

# Restart all workers
echo "Restarting workers..."
docker-compose -f "$COMPOSE_FILE" restart celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance

# Restart API (in case there are changes)
echo "Restarting API..."
docker-compose -f "$COMPOSE_FILE" restart api

echo "✅ Services restarted"
echo ""

##############################################################################
# Wait for Initialization
##############################################################################
echo -e "${BLUE}[4/5] Waiting for services to initialize...${NC}"
echo ""

echo "Waiting 45 seconds for beat to start scheduling and first ping cycle..."
sleep 45

echo "✅ Services initialized"
echo ""

##############################################################################
# Verify Auto-Scaling
##############################################################################
echo -e "${BLUE}[5/5] Verifying auto-scaling is working...${NC}"
echo ""

echo "Checking beat scheduler logs for batched tasks:"
docker-compose -f "$COMPOSE_FILE" logs --tail 20 celery-beat | grep -E "(ping_all_devices_batched|poll_all_devices_snmp_batched|evaluate-alert-rules)" || echo "⚠️  No batched task logs yet (may need more time)"

echo ""
echo "Checking monitoring worker logs for AUTO-SCALING messages:"
docker-compose -f "$COMPOSE_FILE" logs --tail 100 celery-worker-monitoring | grep -E "(AUTO-SCALING|batch size|Scheduling.*batch)" | tail -10 || echo "⚠️  No AUTO-SCALING logs yet (may need more time)"

echo ""
echo "=========================================================================="
echo -e "${GREEN}✅ RESTART COMPLETE!${NC}"
echo "=========================================================================="
echo ""

echo "Container status:"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "=========================================================================="
echo -e "${CYAN}📊 VERIFICATION COMMANDS:${NC}"
echo "=========================================================================="
echo ""
echo "  # Watch for AUTO-SCALING messages (run for 2-3 minutes):"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-worker-monitoring | grep AUTO-SCALING"
echo ""
echo "  # You should see messages like:"
echo "  # AUTO-SCALING: 875 devices → batch size 100 → ~9 batches"
echo "  # Scheduling 9 batch ping tasks for 875 devices"
echo ""
echo "  # Check beat is scheduling batched tasks:"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-beat | grep batched"
echo ""
echo "  # You should see:"
echo "  # Scheduler: Sending due task ping-all-devices (monitoring.tasks.ping_all_devices_batched)"
echo ""
echo "  # Check queue sizes (should stay low < 100):"
echo "  watch -n 5 'docker-compose -f $COMPOSE_FILE exec redis redis-cli -a redispass LLEN monitoring && docker-compose -f $COMPOSE_FILE exec redis redis-cli -a redispass LLEN snmp'"
echo ""
echo "  # Check API health:"
echo "  curl http://localhost:5001/api/v1/health"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

exit 0
