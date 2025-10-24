#!/bin/bash

##############################################################################
# Pre-Deployment Health Check
##############################################################################
# Verifies system is healthy before deploying robustness improvements
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production-priority-queues.yml"

echo "=========================================================================="
echo -e "${BLUE}🔍 PRE-DEPLOYMENT HEALTH CHECK${NC}"
echo "=========================================================================="
echo ""

ISSUES_FOUND=0

##############################################################################
# 1. Check Container Status
##############################################################################
echo -e "${BLUE}[1/5] Checking container status...${NC}"
echo ""

# Check if all containers are running
CONTAINERS=(
    "wardops-postgres-prod"
    "wardops-redis-prod"
    "wardops-victoriametrics-prod"
    "wardops-api-prod"
    "wardops-beat-prod"
    "wardops-worker-alerts-prod"
    "wardops-worker-monitoring-prod"
    "wardops-worker-snmp-prod"
    "wardops-worker-maintenance-prod"
)

for container in "${CONTAINERS[@]}"; do
    STATUS=$(docker ps -a --filter "name=$container" --format "{{.Status}}")

    if [[ "$STATUS" == *"Up"* ]]; then
        if [[ "$STATUS" == *"unhealthy"* ]]; then
            echo -e "  ${YELLOW}⚠️  $container: UNHEALTHY${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        else
            echo -e "  ${GREEN}✅ $container: healthy${NC}"
        fi
    else
        echo -e "  ${RED}❌ $container: NOT RUNNING${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
done

echo ""

##############################################################################
# 2. Check Database Connectivity
##############################################################################
echo -e "${BLUE}[2/5] Checking database connectivity...${NC}"
echo ""

if docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Database is accessible${NC}"
else
    echo -e "  ${RED}❌ Cannot connect to database${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

echo ""

##############################################################################
# 3. Check Redis Connectivity
##############################################################################
echo -e "${BLUE}[3/5] Checking Redis connectivity...${NC}"
echo ""

# Redis has authentication with password "redispass"
if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a redispass PING 2>/dev/null | grep -q "PONG"; then
    echo -e "  ${GREEN}✅ Redis is accessible${NC}"
else
    echo -e "  ${RED}❌ Cannot connect to Redis${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

echo ""

##############################################################################
# 4. Check Worker Activity
##############################################################################
echo -e "${BLUE}[4/5] Checking worker activity...${NC}"
echo ""

# Check if workers are processing tasks
MONITORING_LOGS=$(docker-compose -f "$COMPOSE_FILE" logs --tail 20 celery-worker-monitoring 2>/dev/null || echo "")
ALERTS_LOGS=$(docker-compose -f "$COMPOSE_FILE" logs --tail 20 celery-worker-alerts 2>/dev/null || echo "")

if [[ "$MONITORING_LOGS" == *"Task"* ]] || [[ "$MONITORING_LOGS" == *"Received"* ]]; then
    echo -e "  ${GREEN}✅ Monitoring worker is processing tasks${NC}"
else
    echo -e "  ${YELLOW}⚠️  Monitoring worker has no recent activity${NC}"
fi

if [[ "$ALERTS_LOGS" == *"Task"* ]] || [[ "$ALERTS_LOGS" == *"Received"* ]]; then
    echo -e "  ${GREEN}✅ Alerts worker is processing tasks${NC}"
else
    echo -e "  ${YELLOW}⚠️  Alerts worker has no recent activity${NC}"
fi

echo ""

##############################################################################
# 5. Check API Health
##############################################################################
echo -e "${BLUE}[5/5] Checking API health...${NC}"
echo ""

# Try to access API health endpoint
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/v1/health 2>/dev/null || echo "000")

if [ "$API_STATUS" = "200" ]; then
    echo -e "  ${GREEN}✅ API is responding (HTTP 200)${NC}"
elif [ "$API_STATUS" = "000" ]; then
    echo -e "  ${YELLOW}⚠️  Cannot reach API (connection failed)${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "  ${YELLOW}⚠️  API returned HTTP $API_STATUS${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT${NC}"
    echo "=========================================================================="
    echo ""
    echo "You can now run:"
    echo "  ./deploy-robustness-improvements.sh"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  FOUND $ISSUES_FOUND ISSUE(S) - REVIEW BEFORE DEPLOYMENT${NC}"
    echo "=========================================================================="
    echo ""
    echo -e "${CYAN}RECOMMENDATIONS:${NC}"
    echo ""

    # Check specific unhealthy containers
    if docker ps --filter "name=wardops-api-prod" --format "{{.Status}}" | grep -q "unhealthy"; then
        echo "  📌 API is unhealthy:"
        echo "     Check logs: docker-compose -f $COMPOSE_FILE logs --tail 50 api"
        echo ""
    fi

    if docker ps --filter "name=wardops-beat-prod" --format "{{.Status}}" | grep -q "unhealthy"; then
        echo "  📌 Beat scheduler is unhealthy:"
        echo "     Check logs: docker-compose -f $COMPOSE_FILE logs --tail 50 celery-beat"
        echo "     This may affect task scheduling"
        echo ""
    fi

    if docker ps --filter "name=wardops-worker-maintenance-prod" --format "{{.Status}}" | grep -q "unhealthy"; then
        echo "  📌 Maintenance worker is unhealthy:"
        echo "     Check logs: docker-compose -f $COMPOSE_FILE logs --tail 50 celery-worker-maintenance"
        echo "     This is LOW PRIORITY (maintenance tasks only)"
        echo ""
    fi

    echo -e "${YELLOW}You can still deploy, but some features may not work correctly.${NC}"
    echo ""
    echo "To proceed anyway:"
    echo "  ./deploy-robustness-improvements.sh"
    echo ""

    exit 1
fi
