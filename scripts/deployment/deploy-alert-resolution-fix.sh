#!/bin/bash

##############################################################################
# Deploy Alert Auto-Resolution Fix
##############################################################################
#
# CRITICAL BUG: Alerts with rule_id = NULL never get auto-resolved
#
# ROOT CAUSE:
# - Old alerts created by tasks_batch.py have rule_id = NULL
# - evaluate_alert_rules() queries: WHERE rule_id = :rule_id
# - NULL != :rule_id in SQL, so query doesn't find old alerts
# - Auto-resolution logic never triggers
#
# FIX:
# 1. Update database: Set rule_id for all NULL alerts based on rule_name
# 2. Update code: Use OR condition to match by rule_name as fallback
# 3. Rebuild workers with fixed code
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
echo -e "${RED}🐛 DEPLOYING ALERT AUTO-RESOLUTION FIX${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# Step 1: Show Current Problem
##############################################################################
echo -e "${BLUE}[1/5] Showing current problem state...${NC}"
echo ""

echo "Current alert statistics:"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     COUNT(*) as total_alerts,
     COUNT(rule_id) as with_rule_id,
     COUNT(*) - COUNT(rule_id) as null_rule_id,
     COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as unresolved
   FROM alert_history;"

echo ""
echo "Unresolved alerts with NULL rule_id (these are the problem):"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     rule_name,
     severity,
     COUNT(*) as count,
     MIN(triggered_at) as oldest,
     MAX(triggered_at) as newest
   FROM alert_history
   WHERE rule_id IS NULL
   AND resolved_at IS NULL
   GROUP BY rule_name, severity
   ORDER BY count DESC;"

echo ""

##############################################################################
# Step 2: Fix Database (Set rule_id for NULL alerts)
##############################################################################
echo -e "${BLUE}[2/5] Fixing database: Setting rule_id for NULL alerts...${NC}"
echo ""

echo "Updating 'Ping Unavailable' alerts..."
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "UPDATE alert_history ah
   SET rule_id = ar.id
   FROM alert_rules ar
   WHERE ah.rule_id IS NULL
   AND ah.rule_name = 'Ping Unavailable'
   AND ar.name = 'Ping Unavailable';"

echo "Updating 'Device Down - High Priority' alerts..."
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "UPDATE alert_history ah
   SET rule_id = ar.id
   FROM alert_rules ar
   WHERE ah.rule_id IS NULL
   AND ah.rule_name = 'Device Down - High Priority'
   AND ar.name = 'Device Down - High Priority';"

echo "Updating 'Device Down - Critical' alerts..."
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "UPDATE alert_history ah
   SET rule_id = ar.id
   FROM alert_rules ar
   WHERE ah.rule_id IS NULL
   AND ah.rule_name = 'Device Down - Critical'
   AND ar.name = 'Device Down - Critical';"

echo "Updating 'High Latency' alerts..."
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "UPDATE alert_history ah
   SET rule_id = ar.id
   FROM alert_rules ar
   WHERE ah.rule_id IS NULL
   AND ah.rule_name = 'High Latency'
   AND ar.name = 'High Latency';"

echo ""
echo "✅ Database updated"
echo ""

##############################################################################
# Step 3: Verify Fix
##############################################################################
echo -e "${BLUE}[3/5] Verifying database fix...${NC}"
echo ""

echo "Alert statistics after fix:"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     COUNT(*) as total_alerts,
     COUNT(rule_id) as with_rule_id,
     COUNT(*) - COUNT(rule_id) as null_rule_id_remaining
   FROM alert_history;"

echo ""

##############################################################################
# Step 4: Rebuild Workers with Code Fix
##############################################################################
echo -e "${BLUE}[4/5] Rebuilding workers with code fix...${NC}"
echo ""

echo "Stopping workers..."
docker-compose -f "$COMPOSE_FILE" stop celery-worker-alerts celery-worker-monitoring

echo ""
echo "Rebuilding images with alert resolution fix..."
docker-compose -f "$COMPOSE_FILE" build --no-cache celery-worker-alerts celery-worker-monitoring

echo ""
echo "Starting workers..."
docker-compose -f "$COMPOSE_FILE" start celery-worker-alerts celery-worker-monitoring

echo ""
echo "Waiting 20 seconds for workers to initialize..."
sleep 20

echo "✅ Workers restarted with fix"
echo ""

##############################################################################
# Step 5: Monitor Auto-Resolution
##############################################################################
echo -e "${BLUE}[5/5] Monitoring alert auto-resolution...${NC}"
echo ""

echo "Unresolved alerts by device (should auto-resolve in next 10 seconds):"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     sd.name,
     sd.ip,
     ah.rule_name,
     ah.severity,
     ah.triggered_at,
     NOW() - ah.triggered_at as age
   FROM alert_history ah
   JOIN standalone_devices sd ON ah.device_id = sd.id
   WHERE ah.resolved_at IS NULL
   ORDER BY ah.triggered_at DESC
   LIMIT 10;"

echo ""
echo "Checking alert worker logs for auto-resolution..."
docker-compose -f "$COMPOSE_FILE" logs --tail 50 celery-worker-alerts | grep -E "(RESOLVED|evaluate)" || echo "No recent activity yet"

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ ALERT AUTO-RESOLUTION FIX DEPLOYED!${NC}"
echo "=========================================================================="
echo ""

echo -e "${CYAN}🔧 WHAT WAS FIXED:${NC}"
echo ""
echo "  ✅ Database: Set rule_id for all NULL alerts based on rule_name"
echo "  ✅ Code: Added fallback to match alerts by rule_name"
echo "  ✅ Workers: Rebuilt with fixed code"
echo ""

echo -e "${YELLOW}📊 NEXT ALERT EVALUATION:${NC}"
echo ""
echo "  The next alert evaluation will:"
echo "  1. Find old alerts (now that rule_id is set)"
echo "  2. Check if devices are UP"
echo "  3. Auto-resolve alerts for UP devices"
echo ""
echo "  Expected: Zugdidi2-AP and Zugdidi-2-NVR alerts will be resolved"
echo "  Wait time: ~10 seconds (next evaluation cycle)"
echo ""

echo -e "${CYAN}🔍 VERIFY FIX:${NC}"
echo ""
echo "  # Check if alerts were auto-resolved (wait 30 seconds, then run):"
echo "  docker-compose -f $COMPOSE_FILE exec postgres psql -U ward_admin -d ward_ops -c \\"
echo "    \"SELECT COUNT(*) as unresolved FROM alert_history WHERE resolved_at IS NULL;\""
echo ""
echo "  # Check alert worker logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f celery-worker-alerts | grep RESOLVED"
echo ""
echo "  # Refresh Ward-Ops UI:"
echo "  - Hard refresh browser (Ctrl+Shift+R)"
echo "  - Device status should now be correct"
echo ""

echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

exit 0
