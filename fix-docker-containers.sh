#!/bin/bash

##############################################################################
# Fix Docker Container Corruption Issue
##############################################################################
#
# WHAT THIS DOES:
# - Removes old/corrupted containers causing ContainerConfig error
# - Cleans up orphan containers
# - Recreates all workers with auto-scaling
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
echo -e "${GREEN}🔧 FIXING DOCKER CONTAINER CORRUPTION${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# Stop All Workers
##############################################################################
echo -e "${BLUE}[1/5] Stopping all workers...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" stop celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance celery-beat 2>&1 || true

echo "✅ Workers stopped"
echo ""

##############################################################################
# Remove Old Containers
##############################################################################
echo -e "${BLUE}[2/5] Removing old/corrupted containers...${NC}"
echo ""

# Remove specific old containers
echo "Removing orphan containers..."
docker rm -f wardops-worker-prod 2>&1 || true
docker rm -f 101921dd982a_wardops-beat-prod 2>&1 || true
docker rm -f 648b25800094_wardops-worker-monitoring-prod 2>&1 || true
docker rm -f b91cb4751dd9_wardops-worker-snmp-prod 2>&1 || true

# Remove current containers (they may be corrupted)
echo "Removing current containers..."
docker-compose -f "$COMPOSE_FILE" rm -f celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance celery-beat 2>&1 || true

echo "✅ Old containers removed"
echo ""

##############################################################################
# Clean Up Orphans
##############################################################################
echo -e "${BLUE}[3/5] Cleaning up orphan containers...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>&1 || true

echo "✅ Orphan containers cleaned"
echo ""

##############################################################################
# Rebuild Images
##############################################################################
echo -e "${BLUE}[4/5] Rebuilding worker images...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" build --no-cache celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance celery-beat

echo "✅ Images rebuilt"
echo ""

##############################################################################
# Start Fresh Workers
##############################################################################
echo -e "${BLUE}[5/5] Starting fresh auto-scaling workers...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" up -d celery-worker-monitoring celery-worker-snmp celery-worker-alerts celery-worker-maintenance celery-beat

echo "Waiting 30 seconds for workers to initialize..."
sleep 30

echo "✅ Workers started"
echo ""

##############################################################################
# Verify Workers
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ DOCKER CONTAINERS FIXED${NC}"
echo "=========================================================================="
echo ""

echo "Container status:"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "Waiting 35 seconds for first ping cycle..."
sleep 35

echo ""
echo "Checking for auto-scaling messages:"
docker-compose -f "$COMPOSE_FILE" logs --tail 100 celery-worker-monitoring | grep -E "(AUTO-SCALING|batch size)" | tail -5

echo ""
echo "=========================================================================="
echo -e "${GREEN}🚀 AUTO-SCALING DEPLOYMENT COMPLETE!${NC}"
echo "=========================================================================="
echo ""
echo -e "${CYAN}📊 Monitor Auto-Scaling:${NC}"
echo ""
echo "  # Watch auto-scaling decisions (run for 2-3 minutes):"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-worker-monitoring | grep AUTO-SCALING"
echo ""
echo "  # You should see messages like:"
echo "  # AUTO-SCALING: 875 devices → batch size 100 → ~9 batches"
echo ""
echo "  # Check queue sizes (should stay low):"
echo "  watch -n 5 'docker-compose -f $COMPOSE_FILE exec redis redis-cli -a redispass LLEN monitoring snmp'"
echo ""
echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

exit 0
