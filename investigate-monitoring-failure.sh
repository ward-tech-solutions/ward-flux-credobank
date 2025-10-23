#!/bin/bash

##############################################################################
# EMERGENCY: Investigate Complete Monitoring Failure
##############################################################################
#
# PROBLEM: ALL alerts missed today - Zabbix catching everything, WARD OPS nothing
# This is NOT just one device - this is COMPLETE monitoring failure
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
echo -e "${RED}🚨 EMERGENCY: COMPLETE MONITORING FAILURE INVESTIGATION${NC}"
echo "=========================================================================="
echo ""
echo "⏰ Investigation started at: $(date)"
echo ""

##############################################################################
# Step 1: Check Recent Ping Activity
##############################################################################
echo -e "${BLUE}[1/7] Checking recent ping activity (last 2 hours)...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U wardops -d wardops <<'SQL'
SELECT
  COUNT(*) as total_pings_last_2h,
  COUNT(DISTINCT device_ip) as unique_devices_pinged,
  MAX(timestamp) as latest_ping,
  NOW() - MAX(timestamp) as time_since_last_ping
FROM ping_results
WHERE timestamp > NOW() - INTERVAL '2 hours';
SQL

echo ""

##############################################################################
# Step 2: Check When Monitoring Stopped
##############################################################################
echo -e "${BLUE}[2/7] Finding when monitoring stopped...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U wardops -d wardops <<'SQL'
-- Show ping activity by hour for last 24 hours
SELECT
  date_trunc('hour', timestamp) as hour,
  COUNT(*) as pings_count,
  COUNT(DISTINCT device_ip) as devices_pinged
FROM ping_results
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
SQL

echo ""

##############################################################################
# Step 3: Check Beat Scheduler Status
##############################################################################
echo -e "${BLUE}[3/7] Checking Beat scheduler (should schedule every 30s)...${NC}"
echo ""

echo "Last 30 beat log entries:"
docker-compose -f "$COMPOSE_FILE" logs --tail 30 celery-beat | grep -E "(ping-all-devices|Scheduler)"

echo ""

##############################################################################
# Step 4: Check Worker Status
##############################################################################
echo -e "${BLUE}[4/7] Checking Worker status and recent activity...${NC}"
echo ""

echo "Container status:"
docker-compose -f "$COMPOSE_FILE" ps celery-worker celery-beat

echo ""
echo "Worker ping activity (last 100 lines):"
docker-compose -f "$COMPOSE_FILE" logs --tail 100 celery-worker | grep -c "Pinged" || echo "0 pings found"

echo ""

##############################################################################
# Step 5: Check for Errors in Worker
##############################################################################
echo -e "${BLUE}[5/7] Checking for errors in worker logs...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" logs --tail 200 celery-worker | grep -i "error" | tail -20

echo ""

##############################################################################
# Step 6: Check Monitoring Profile
##############################################################################
echo -e "${BLUE}[6/7] Checking monitoring profile status...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U wardops -d wardops <<'SQL'
SELECT id, name, is_active, created_at
FROM monitoring_profiles
ORDER BY created_at DESC
LIMIT 5;
SQL

echo ""

##############################################################################
# Step 7: Check Total Enabled Devices
##############################################################################
echo -e "${BLUE}[7/7] Checking total enabled devices...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U wardops -d wardops <<'SQL'
SELECT
  COUNT(*) as total_devices,
  COUNT(*) FILTER (WHERE enabled = true) as enabled_devices,
  COUNT(*) FILTER (WHERE enabled = false) as disabled_devices
FROM standalone_devices;
SQL

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${YELLOW}📊 INVESTIGATION SUMMARY${NC}"
echo "=========================================================================="
echo ""
echo "Key Questions to Answer:"
echo ""
echo "1. How many pings in last 2 hours? (Should be ~240 per device)"
echo "2. When did pings stop? (Check hourly breakdown)"
echo "3. Is Beat scheduling ping-all-devices every 30s?"
echo "4. Is Worker processing ping tasks?"
echo "5. Are there errors in worker logs?"
echo "6. Is monitoring profile active?"
echo "7. How many devices should be monitored?"
echo ""
echo "⏰ Investigation completed at: $(date)"
echo "=========================================================================="
echo ""

exit 0
