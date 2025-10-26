#!/bin/bash
#######################################################
# Check Device Status Timing - Diagnostic Script
# Shows when devices went down, when alerts triggered,
# and how long it took
#######################################################

echo "=========================================="
echo "  DEVICE STATUS TIMING ANALYSIS"
echo "  $(date)"
echo "=========================================="
echo ""

# 1. Check current device status
echo "=== 1. CURRENT DEVICE STATUS (Chiatura devices) ==="
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
  name,
  ip,
  down_since,
  CASE WHEN down_since IS NULL THEN 'UP' ELSE 'DOWN' END as current_status,
  CASE
    WHEN down_since IS NOT NULL
    THEN EXTRACT(EPOCH FROM (NOW() - down_since))/60
    ELSE NULL
  END as minutes_down
FROM standalone_devices
WHERE name LIKE '%Chiatura%'
  AND ip IN ('10.195.49.248', '10.195.49.249', '10.199.49.140', '10.195.49.252')
ORDER BY name, ip;
"
echo ""

# 2. Check recent alert history for these devices
echo "=== 2. RECENT ALERT HISTORY (Last 30 minutes) ==="
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
  d.name,
  d.ip,
  ah.severity,
  ah.message,
  ah.triggered_at,
  ah.resolved_at,
  EXTRACT(EPOCH FROM (COALESCE(ah.resolved_at, NOW()) - ah.triggered_at))/60 as duration_minutes,
  CASE WHEN ah.resolved_at IS NULL THEN 'ACTIVE' ELSE 'RESOLVED' END as alert_status
FROM alert_history ah
JOIN standalone_devices d ON ah.device_id = d.id
WHERE d.name LIKE '%Chiatura%'
  AND d.ip IN ('10.195.49.248', '10.195.49.249', '10.199.49.140', '10.195.49.252')
  AND ah.triggered_at > NOW() - INTERVAL '30 minutes'
ORDER BY ah.triggered_at DESC;
"
echo ""

# 3. Check ping results from VictoriaMetrics (last 30 minutes)
echo "=== 3. PING STATUS FROM VICTORIAMETRICS (Last 30 min) ==="
echo "Querying VictoriaMetrics for ping status..."

# Query each device
for IP in "10.195.49.248" "10.195.49.249" "10.199.49.140" "10.195.49.252"; do
  echo ""
  echo "Device: $IP"
  curl -s "http://localhost:8428/api/v1/query_range?query=device_ping_status{device_ip=\"$IP\"}&start=$(date -u -d '30 minutes ago' +%s)&end=$(date -u +%s)&step=60" | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('status') == 'success' and data.get('data', {}).get('result'):
    result = data['data']['result'][0]
    values = result['values']
    print(f\"  Total data points: {len(values)}\")

    # Show recent status changes
    prev_status = None
    changes = []
    for ts, val in values:
        status = 'UP' if float(val) == 1 else 'DOWN'
        if status != prev_status and prev_status is not None:
            from datetime import datetime
            changes.append(f\"    {datetime.fromtimestamp(int(ts)).strftime('%H:%M:%S')} - Changed to {status}\")
        prev_status = status

    if changes:
        print(\"  Status changes:\")
        for change in changes[-10:]:  # Last 10 changes
            print(change)
    else:
        print(f\"  No status changes (stable {prev_status})\")
else:
    print('  No data available')
" 2>/dev/null || echo "  Error querying VictoriaMetrics"
done
echo ""

# 4. Check worker logs for these specific devices
echo "=== 4. WORKER LOGS (Last 5 minutes) ==="
echo "Looking for status changes in worker logs..."
docker logs --since 5m wardops-worker-monitoring-prod 2>&1 | \
  grep -E "(Chiatura.*went DOWN|Chiatura.*RECOVERED|10.195.49.248|10.195.49.249|10.199.49.140|10.195.49.252)" | \
  tail -20
echo ""

# 5. Timing summary
echo "=== 5. TIMING SUMMARY ==="
echo ""
echo "Expected Behavior:"
echo "  • Ping interval: 10 seconds"
echo "  • Device goes DOWN → Detected within 0-10 seconds"
echo "  • Alert created: Immediately after detection"
echo "  • Cache cleared: Immediately after status change"
echo "  • UI updates: Within 1-2 seconds (after cache clear)"
echo ""
echo "Total latency: 10-20 seconds from physical outage to UI update"
echo ""
echo "Compare with Zabbix:"
echo "  • Check the Zabbix timestamps you showed earlier"
echo "  • WARD should be within 10-20 seconds of Zabbix"
echo ""
echo "=========================================="
