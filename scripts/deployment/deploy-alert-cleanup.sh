#!/bin/bash

##############################################################################
# Deploy Automatic Alert Cleanup (7-Day Retention)
##############################################################################
#
# WHAT THIS DOES:
# 1. Runs manual cleanup to remove old resolved alerts (>7 days)
# 2. Enables automatic weekly cleanup (Sundays 3:30 AM)
# 3. Frees up database space and improves query performance
#
# SAFE TO RUN:
# - Only deletes RESOLVED alerts older than 7 days
# - Keeps ALL unresolved alerts (regardless of age)
# - No impact on active monitoring
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
echo -e "${GREEN}🧹 DEPLOYING AUTOMATIC ALERT CLEANUP${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Started at: $(date)"
echo ""

##############################################################################
# Step 1: Show Current Database State
##############################################################################
echo -e "${BLUE}[1/5] Checking current database state...${NC}"
echo ""

echo "Current alert statistics:"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     COUNT(*) as total_alerts,
     COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as unresolved,
     COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved,
     COUNT(CASE WHEN resolved_at < NOW() - INTERVAL '7 days' THEN 1 END) as resolved_older_than_7d,
     pg_size_pretty(pg_total_relation_size('alert_history')) as total_size
   FROM alert_history;"

echo ""

##############################################################################
# Step 2: Run Manual Cleanup
##############################################################################
echo -e "${BLUE}[2/5] Running manual cleanup (deleting resolved alerts >7 days old)...${NC}"
echo ""

echo "Preview of alerts to be deleted:"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     DATE(resolved_at) as date,
     COUNT(*) as alerts_to_delete
   FROM alert_history
   WHERE resolved_at IS NOT NULL
   AND resolved_at < NOW() - INTERVAL '7 days'
   GROUP BY DATE(resolved_at)
   ORDER BY date
   LIMIT 10;"

echo ""
echo "Deleting old resolved alerts..."
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "DELETE FROM alert_history
   WHERE resolved_at IS NOT NULL
   AND resolved_at < NOW() - INTERVAL '7 days';"

echo ""
echo "✅ Manual cleanup complete"
echo ""

##############################################################################
# Step 3: Vacuum Database
##############################################################################
echo -e "${BLUE}[3/5] Reclaiming disk space (VACUUM)...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "VACUUM ANALYZE alert_history;"

echo "✅ Disk space reclaimed"
echo ""

##############################################################################
# Step 4: Show Results
##############################################################################
echo -e "${BLUE}[4/5] Showing results after cleanup...${NC}"
echo ""

echo "Alert statistics after cleanup:"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     COUNT(*) as total_alerts_remaining,
     COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as unresolved,
     COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved_last_7d,
     pg_size_pretty(pg_total_relation_size('alert_history')) as total_size_after
   FROM alert_history;"

echo ""

##############################################################################
# Step 5: Enable Automatic Weekly Cleanup
##############################################################################
echo -e "${BLUE}[5/5] Enabling automatic weekly cleanup...${NC}"
echo ""

echo "Rebuilding workers to enable automatic cleanup..."
docker-compose -f "$COMPOSE_FILE" build --no-cache celery-worker-maintenance celery-beat

echo ""
echo "Restarting maintenance worker and beat scheduler..."
docker-compose -f "$COMPOSE_FILE" restart celery-worker-maintenance celery-beat

echo ""
echo "Waiting 10 seconds for services to start..."
sleep 10

echo "✅ Automatic cleanup enabled"
echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${GREEN}✅ ALERT CLEANUP DEPLOYED SUCCESSFULLY!${NC}"
echo "=========================================================================="
echo ""

echo -e "${CYAN}📊 WHAT WAS DONE:${NC}"
echo ""
echo "  ✅ Deleted old resolved alerts (>7 days)"
echo "  ✅ Reclaimed database disk space (VACUUM)"
echo "  ✅ Enabled automatic weekly cleanup (Sundays 3:30 AM)"
echo ""

echo -e "${YELLOW}🔄 AUTOMATIC CLEANUP SCHEDULE:${NC}"
echo ""
echo "  When: Every Sunday at 3:30 AM (UTC)"
echo "  What: Deletes resolved alerts older than 7 days"
echo "  Safe: Keeps ALL unresolved alerts (regardless of age)"
echo ""

echo -e "${CYAN}📈 MONITORING:${NC}"
echo ""
echo "  # Check next scheduled cleanup:"
echo "  docker-compose -f $COMPOSE_FILE exec celery-beat celery -A celery_app inspect scheduled"
echo ""
echo "  # Check cleanup history:"
echo "  docker-compose -f $COMPOSE_FILE logs celery-worker-maintenance | grep 'Alert cleanup complete'"
echo ""
echo "  # Manually trigger cleanup (if needed):"
echo "  docker-compose -f $COMPOSE_FILE exec celery-worker-maintenance celery -A celery_app call maintenance.cleanup_old_alerts --kwargs '{\"days\": 7}'"
echo ""

echo "⏰ Completed at: $(date)"
echo "=========================================================================="
echo ""

exit 0
