#!/bin/bash

##############################################################################
# Diagnose Live Issue - Why Ward-Ops Shows UP When Zabbix Shows DOWN
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production-priority-queues.yml"

# Devices reported DOWN by Zabbix
DEVICE1_IP="10.195.74.252"  # Zugdidi2-AP
DEVICE1_NAME="Zugdidi2-AP"
DEVICE2_IP="10.199.74.140"  # Zugdidi-2-NVR
DEVICE2_NAME="Zugdidi-2-NVR"

echo "=========================================================================="
echo -e "${RED}🚨 LIVE ISSUE DIAGNOSIS${NC}"
echo "=========================================================================="
echo ""
echo "Zabbix reported these devices DOWN at 09:34 (2025.10.24):"
echo "  - $DEVICE1_NAME ($DEVICE1_IP)"
echo "  - $DEVICE2_NAME ($DEVICE2_IP)"
echo ""
echo "Ward-Ops shows them as UP - Let's find out why..."
echo ""

##############################################################################
# 1. Check Latest Ping Results from Database
##############################################################################
echo -e "${BLUE}[1/6] Checking latest ping results in database...${NC}"
echo ""

echo "Device 1: $DEVICE1_NAME ($DEVICE1_IP)"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     device_ip,
     is_reachable,
     timestamp,
     NOW() - timestamp as age
   FROM ping_results
   WHERE device_ip = '$DEVICE1_IP'
   ORDER BY timestamp DESC
   LIMIT 5;"

echo ""
echo "Device 2: $DEVICE2_NAME ($DEVICE2_IP)"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     device_ip,
     is_reachable,
     timestamp,
     NOW() - timestamp as age
   FROM ping_results
   WHERE device_ip = '$DEVICE2_IP'
   ORDER BY timestamp DESC
   LIMIT 5;"

echo ""

##############################################################################
# 2. Check Device down_since Status
##############################################################################
echo -e "${BLUE}[2/6] Checking device down_since field...${NC}"
echo ""

echo "Device 1: $DEVICE1_NAME"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     name,
     ip,
     down_since,
     enabled,
     last_seen
   FROM standalone_devices
   WHERE ip = '$DEVICE1_IP';"

echo ""
echo "Device 2: $DEVICE2_NAME"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     name,
     ip,
     down_since,
     enabled,
     last_seen
   FROM standalone_devices
   WHERE ip = '$DEVICE2_IP';"

echo ""

##############################################################################
# 3. Check When Last Ping Task Ran
##############################################################################
echo -e "${BLUE}[3/6] Checking when ping tasks last executed...${NC}"
echo ""

echo "Last 10 ping results (any device):"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     device_ip,
     is_reachable,
     timestamp,
     NOW() - timestamp as age
   FROM ping_results
   ORDER BY timestamp DESC
   LIMIT 10;"

echo ""

##############################################################################
# 4. Check Alert History for These Devices
##############################################################################
echo -e "${BLUE}[4/6] Checking alert history...${NC}"
echo ""

echo "Alerts for $DEVICE1_NAME in last 24 hours:"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     rule_name,
     severity,
     triggered_at,
     resolved_at,
     NOW() - triggered_at as age
   FROM alert_history ah
   JOIN standalone_devices sd ON ah.device_id = sd.id
   WHERE sd.ip = '$DEVICE1_IP'
   AND triggered_at > NOW() - INTERVAL '24 hours'
   ORDER BY triggered_at DESC
   LIMIT 5;"

echo ""
echo "Alerts for $DEVICE2_NAME in last 24 hours:"
docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     rule_name,
     severity,
     triggered_at,
     resolved_at,
     NOW() - triggered_at as age
   FROM alert_history ah
   JOIN standalone_devices sd ON ah.device_id = sd.id
   WHERE sd.ip = '$DEVICE2_IP'
   AND triggered_at > NOW() - INTERVAL '24 hours'
   ORDER BY triggered_at DESC
   LIMIT 5;"

echo ""

##############################################################################
# 5. Check Worker Logs for Ping Activity
##############################################################################
echo -e "${BLUE}[5/6] Checking worker logs for recent ping activity...${NC}"
echo ""

echo "Last 20 lines from monitoring worker:"
docker-compose -f "$COMPOSE_FILE" logs --tail 20 celery-worker-monitoring | grep -E "(ping|batch|Task)" || echo "No recent ping activity found"

echo ""
echo "Last 20 lines from alerts worker:"
docker-compose -f "$COMPOSE_FILE" logs --tail 20 celery-worker-alerts | grep -E "(alert|evaluate)" || echo "No recent alert activity found"

echo ""

##############################################################################
# 6. Check Beat Scheduler
##############################################################################
echo -e "${BLUE}[6/6] Checking beat scheduler for task scheduling...${NC}"
echo ""

echo "Last 30 lines from beat scheduler:"
docker-compose -f "$COMPOSE_FILE" logs --tail 30 celery-beat | grep -E "(ping|alert|Scheduler)" || echo "No scheduler activity found"

echo ""

##############################################################################
# Diagnosis Summary
##############################################################################
echo "=========================================================================="
echo -e "${CYAN}🔍 POSSIBLE ROOT CAUSES:${NC}"
echo "=========================================================================="
echo ""
echo "1. ❌ Ping tasks NOT running"
echo "   - Check: Are ping_results being created?"
echo "   - Check: Is monitoring worker processing tasks?"
echo ""
echo "2. ❌ Database not being updated"
echo "   - Check: When was last ping_result timestamp?"
echo "   - Check: Is down_since NULL when it should have a value?"
echo ""
echo "3. ❌ Alert evaluation NOT running"
echo "   - Check: Are alerts being created?"
echo "   - Check: Is alerts worker processing tasks?"
echo ""
echo "4. ❌ Frontend caching old data"
echo "   - Check: Are API queries returning correct data?"
echo "   - Solution: Hard refresh browser (Ctrl+Shift+R)"
echo ""
echo "5. ❌ Race condition"
echo "   - Ping result inserted but down_since not updated"
echo "   - Transaction not committed"
echo ""
echo "6. ❌ Ping timeout too short (1 second)"
echo "   - Device may be slow to respond"
echo "   - False negative: Device is UP but doesn't respond in 1s"
echo ""

echo -e "${YELLOW}NEXT STEPS:${NC}"
echo ""
echo "Review the data above to identify the root cause."
echo "Then deploy robustness improvements:"
echo "  ./deploy-robustness-improvements.sh"
echo ""

exit 0
