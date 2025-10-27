#!/bin/bash

##############################################################################
# Analyze Why 1,287 Alerts Are Still Unresolved
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
echo -e "${BLUE}🔍 ANALYZING UNRESOLVED ALERTS${NC}"
echo "=========================================================================="
echo ""

##############################################################################
# 1. Overall Statistics
##############################################################################
echo -e "${BLUE}[1/6] Overall alert statistics...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     COUNT(*) as total_alerts,
     COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as unresolved,
     COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved,
     ROUND(100.0 * COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) / COUNT(*), 2) as unresolved_pct
   FROM alert_history;"

echo ""

##############################################################################
# 2. Unresolved Alerts by Rule
##############################################################################
echo -e "${BLUE}[2/6] Unresolved alerts by rule type...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     rule_name,
     severity,
     COUNT(*) as count,
     MIN(triggered_at) as oldest_alert,
     MAX(triggered_at) as newest_alert
   FROM alert_history
   WHERE resolved_at IS NULL
   GROUP BY rule_name, severity
   ORDER BY count DESC;"

echo ""

##############################################################################
# 3. Top 20 Devices with Unresolved Alerts
##############################################################################
echo -e "${BLUE}[3/6] Top 20 devices with most unresolved alerts...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     sd.name,
     sd.ip,
     COUNT(*) as unresolved_alerts,
     STRING_AGG(DISTINCT ah.rule_name, ', ') as alert_types
   FROM alert_history ah
   JOIN standalone_devices sd ON ah.device_id = sd.id
   WHERE ah.resolved_at IS NULL
   GROUP BY sd.name, sd.ip
   ORDER BY unresolved_alerts DESC
   LIMIT 20;"

echo ""

##############################################################################
# 4. Check Recent Ping Results for Top Alerting Devices
##############################################################################
echo -e "${BLUE}[4/6] Current ping status for top 10 alerting devices...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "WITH top_devices AS (
     SELECT sd.ip, sd.name, COUNT(*) as alert_count
     FROM alert_history ah
     JOIN standalone_devices sd ON ah.device_id = sd.id
     WHERE ah.resolved_at IS NULL
     GROUP BY sd.ip, sd.name
     ORDER BY alert_count DESC
     LIMIT 10
   )
   SELECT
     td.name,
     td.ip,
     td.alert_count,
     pr.is_reachable,
     pr.timestamp,
     NOW() - pr.timestamp as age
   FROM top_devices td
   LEFT JOIN LATERAL (
     SELECT is_reachable, timestamp
     FROM ping_results
     WHERE device_ip = td.ip
     ORDER BY timestamp DESC
     LIMIT 1
   ) pr ON true
   ORDER BY td.alert_count DESC;"

echo ""

##############################################################################
# 5. Check for Flapping Devices (State Changes in Last Hour)
##############################################################################
echo -e "${BLUE}[5/6] Detecting flapping devices (3+ state changes in last hour)...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "WITH ping_with_changes AS (
     SELECT
       device_ip,
       is_reachable,
       LAG(is_reachable) OVER (PARTITION BY device_ip ORDER BY timestamp) as prev_reachable,
       timestamp
     FROM ping_results
     WHERE timestamp > NOW() - INTERVAL '1 hour'
   ),
   state_changes AS (
     SELECT
       device_ip,
       COUNT(*) FILTER (WHERE is_reachable != prev_reachable) as changes,
       COUNT(*) as total_pings
     FROM ping_with_changes
     GROUP BY device_ip
   )
   SELECT
     sd.name,
     sc.device_ip,
     sc.changes as state_changes,
     sc.total_pings,
     CASE
       WHEN sc.changes >= 10 THEN 'SEVERE FLAPPING'
       WHEN sc.changes >= 5 THEN 'MODERATE FLAPPING'
       WHEN sc.changes >= 3 THEN 'MINOR FLAPPING'
       ELSE 'STABLE'
     END as status
   FROM state_changes sc
   JOIN standalone_devices sd ON sc.device_ip = sd.ip
   WHERE sc.changes >= 3
   ORDER BY sc.changes DESC
   LIMIT 20;"

echo ""

##############################################################################
# 6. Alert Resolution Rate (Last 24 Hours)
##############################################################################
echo -e "${BLUE}[6/6] Alert resolution rate in last 24 hours...${NC}"
echo ""

docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U ward_admin -d ward_ops -c \
  "SELECT
     COUNT(*) as total_alerts_24h,
     COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) as resolved,
     COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as still_unresolved,
     ROUND(100.0 * COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) / COUNT(*), 2) as resolution_rate_pct,
     ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - triggered_at)) / 60), 2) as avg_resolution_time_minutes
   FROM alert_history
   WHERE triggered_at > NOW() - INTERVAL '24 hours';"

echo ""

##############################################################################
# Summary
##############################################################################
echo "=========================================================================="
echo -e "${CYAN}📊 ANALYSIS SUMMARY${NC}"
echo "=========================================================================="
echo ""
echo "Review the data above to determine:"
echo ""
echo "  1. Are devices ACTUALLY DOWN?"
echo "     - Check ping_results: is_reachable = false means device is truly down"
echo "     - Check Zabbix: Does it show same devices as DOWN?"
echo ""
echo "  2. Are devices FLAPPING?"
echo "     - Look for devices with 3+ state changes per hour"
echo "     - Flapping detection should suppress these alerts"
echo ""
echo "  3. Is auto-resolution working?"
echo "     - Check resolution rate: Should be > 50% in 24 hours"
echo "     - Check avg resolution time: Should be < 10 minutes"
echo ""
echo "  4. Are there network issues?"
echo "     - Look at oldest_alert times: Mass outages at same time?"
echo "     - Check if specific subnets are affected"
echo ""

echo ""
exit 0
