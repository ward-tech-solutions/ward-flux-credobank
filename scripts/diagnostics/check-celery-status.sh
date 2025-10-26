#!/bin/bash

##############################################################################
# Quick Celery Status Check
##############################################################################

echo "==================================================================="
echo "CELERY STATUS CHECK"
echo "==================================================================="
echo ""

echo "1. Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(worker|beat|NAME)"

echo ""
echo "2. Recent Worker Logs (last 30 lines with ping):"
docker logs wardops-worker-prod --tail 100 2>&1 | grep -i "ping" | tail -30

echo ""
echo "3. Recent Beat Logs (last 20 lines):"
docker logs wardops-beat-prod --tail 20 2>&1

echo ""
echo "4. Latest Ping Results (last 5 pings):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT device_name, device_ip, is_reachable, timestamp, NOW() - timestamp AS age
FROM ping_results
ORDER BY timestamp DESC
LIMIT 5;
"

echo ""
echo "5. Active Celery Tasks:"
docker exec wardops-worker-prod celery -A celery_app inspect active 2>/dev/null || echo "Could not inspect"

echo ""
echo "==================================================================="
echo ""

