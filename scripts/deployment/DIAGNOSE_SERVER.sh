#!/bin/bash
# ============================================================================
# WARD OPS CredoBank Server Diagnostic Script
# ============================================================================
# Run this on the CredoBank server to diagnose database and monitoring issues
# ============================================================================

echo "============================================================================"
echo "WARD OPS - CredoBank Server Diagnostics"
echo "============================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# 1. Container Status
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. CONTAINER STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# ============================================================================
# 2. Database Tables
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. DATABASE TABLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking if tables exist..."
TABLES=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public';" 2>&1)

if echo "$TABLES" | grep -q "devices"; then
  echo -e "${GREEN}✅ Tables exist${NC}"
  echo ""
  echo "All tables:"
  docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "\dt"
else
  echo -e "${RED}❌ TABLES DO NOT EXIST!${NC}"
  echo ""
  echo "Error output:"
  echo "$TABLES"
  echo ""
  echo -e "${YELLOW}This means database seeding FAILED during startup!${NC}"
fi
echo ""

# ============================================================================
# 3. Database Seeding Status
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. DATABASE SEEDING STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking API logs for seeding activity..."
echo ""

SEED_LOGS=$(docker logs wardops-api-prod 2>&1 | grep -i "seeding\|seed_core\|seed_credobank\|migrations")

if [ -n "$SEED_LOGS" ]; then
  echo "Seeding logs found:"
  echo "$SEED_LOGS" | tail -30
else
  echo -e "${YELLOW}⚠️  No seeding logs found - container may not have started properly${NC}"
fi
echo ""

# Check for errors
ERROR_LOGS=$(docker logs wardops-api-prod 2>&1 | grep -i "error\|exception\|failed" | head -20)
if [ -n "$ERROR_LOGS" ]; then
  echo -e "${RED}Errors found in API logs:${NC}"
  echo "$ERROR_LOGS"
else
  echo -e "${GREEN}✅ No errors in API logs${NC}"
fi
echo ""

# ============================================================================
# 4. Device Count
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. DEVICE COUNT (Expected: 875)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DEVICE_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM devices;" 2>&1)

if echo "$DEVICE_COUNT" | grep -qE "^[0-9]+$"; then
  DEVICE_COUNT=$(echo "$DEVICE_COUNT" | tr -d ' ')
  if [ "$DEVICE_COUNT" -eq 875 ]; then
    echo -e "${GREEN}✅ Devices seeded correctly: $DEVICE_COUNT / 875${NC}"
  else
    echo -e "${YELLOW}⚠️  Device count mismatch: $DEVICE_COUNT / 875${NC}"
  fi
else
  echo -e "${RED}❌ ERROR: Cannot query devices table${NC}"
  echo "$DEVICE_COUNT"
fi
echo ""

# ============================================================================
# 5. SNMP vs ICMP Devices
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. SNMP vs ICMP MONITORING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
  CASE
    WHEN snmp_community IS NOT NULL AND snmp_community != '' THEN 'SNMP + ICMP'
    ELSE 'ICMP Only'
  END as monitoring_type,
  COUNT(*) as device_count
FROM devices
GROUP BY monitoring_type;" 2>&1 || echo -e "${RED}❌ Cannot query devices table${NC}"
echo ""

# ============================================================================
# 6. Monitoring Tasks
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. MONITORING TASKS (Last 10 seconds of activity)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking worker logs for ping tasks..."
PING_TASKS=$(docker logs wardops-worker-prod 2>&1 | grep "ping_device.*succeeded" | tail -5)

if [ -n "$PING_TASKS" ]; then
  echo -e "${GREEN}✅ Ping monitoring is working${NC}"
  echo ""
  echo "Recent ping results:"
  echo "$PING_TASKS"
else
  echo -e "${RED}❌ No ping tasks found${NC}"
fi
echo ""

# Check for SNMP tasks
echo "Checking for SNMP monitoring tasks..."
SNMP_TASKS=$(docker logs wardops-worker-prod 2>&1 | grep -i "snmp" | tail -5)

if [ -n "$SNMP_TASKS" ]; then
  echo -e "${GREEN}✅ SNMP monitoring is active${NC}"
  echo "$SNMP_TASKS"
else
  echo -e "${YELLOW}⚠️  No SNMP tasks found (may be ICMP-only mode)${NC}"
fi
echo ""

# ============================================================================
# 7. Health Checks
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. HEALTH CHECKS (Last 10 minutes)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
  COUNT(*) as total_checks,
  COUNT(DISTINCT device_id) as devices_monitored,
  MIN(created_at) as earliest_check,
  MAX(created_at) as latest_check
FROM device_health_checks
WHERE created_at > NOW() - INTERVAL '10 minutes';" 2>&1 || echo -e "${RED}❌ Cannot query device_health_checks table${NC}"
echo ""

# ============================================================================
# 8. Celery Worker Stats
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. CELERY WORKER STATS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking celery worker status..."
docker exec wardops-worker-prod celery -A celery_app inspect stats 2>&1 | head -30 || echo -e "${RED}❌ Cannot inspect celery worker${NC}"
echo ""

# ============================================================================
# 9. Environment Configuration
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9. ENVIRONMENT CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DATABASE_URL:               $(docker exec wardops-api-prod env | grep DATABASE_URL | cut -d'@' -f2)"
echo "MONITORING_MODE:            $(docker exec wardops-api-prod env | grep MONITORING_MODE || echo 'Not set')"
echo "CELERY_WORKER_CONCURRENCY:  $(docker exec wardops-api-prod env | grep CELERY_WORKER_CONCURRENCY || echo 'Not set')"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DIAGNOSTIC SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if database tables exist
if echo "$TABLES" | grep -q "devices"; then
  echo -e "${GREEN}✅ Database tables exist${NC}"

  # Check device count
  if [ "$DEVICE_COUNT" -eq 875 ]; then
    echo -e "${GREEN}✅ All 875 devices seeded${NC}"
  else
    echo -e "${YELLOW}⚠️  Device count: $DEVICE_COUNT / 875${NC}"
  fi

  # Check if monitoring is working
  if [ -n "$PING_TASKS" ]; then
    echo -e "${GREEN}✅ ICMP monitoring is working${NC}"
  else
    echo -e "${RED}❌ ICMP monitoring NOT working${NC}"
  fi
else
  echo -e "${RED}❌ CRITICAL: Database tables do not exist!${NC}"
  echo ""
  echo "ACTION REQUIRED:"
  echo "1. Check API container logs:"
  echo "   docker logs wardops-api-prod 2>&1 | less"
  echo ""
  echo "2. Manually run seeding:"
  echo "   docker exec wardops-api-prod python3 /app/scripts/seed_core.py"
  echo "   docker exec wardops-api-prod python3 /app/scripts/seed_credobank.py"
  echo ""
  echo "3. Restart containers:"
  echo "   cd ward-flux-credobank"
  echo "   docker-compose -f docker-compose.production-local.yml restart"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Diagnostics complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
