#!/bin/bash

echo "================================================================"
echo "  DEPLOYMENT VERIFICATION"
echo "================================================================"
echo ""

echo "1. Worker Configuration:"
echo "----------------------------------------------------------------"
docker logs wardops-worker-prod 2>&1 | grep -E "concurrency|pool" | head -5

echo ""
echo "2. Worker Process Count:"
echo "----------------------------------------------------------------"
docker exec wardops-worker-prod ps aux | grep -c "celery worker" || echo "N/A"

echo ""
echo "3. Beat Scheduler Status:"
echo "----------------------------------------------------------------"
docker logs wardops-beat-prod --tail 20 2>&1 | grep -E "ERROR|Scheduler|ready"

echo ""
echo "4. Current Queue Depth:"
echo "----------------------------------------------------------------"
QUEUE=$(docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery 2>/dev/null)
echo "Queue: $QUEUE tasks"

echo ""
echo "5. Active Worker Tasks:"
echo "----------------------------------------------------------------"
docker exec wardops-worker-prod celery -A celery_app inspect active 2>/dev/null | grep -c "monitoring.tasks" || echo "0"

echo ""
echo "6. Container Health:"
echo "----------------------------------------------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "================================================================"
