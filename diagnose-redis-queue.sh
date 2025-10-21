#!/bin/bash

echo "================================================================"
echo "  REDIS QUEUE DIAGNOSTICS"
echo "================================================================"
echo ""

# Check all Redis keys
echo "All Redis keys:"
docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning KEYS '*' 2>/dev/null | head -20

echo ""
echo "----------------------------------------------------------------"
echo "Celery-related keys:"
docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning KEYS 'celery*' 2>/dev/null

echo ""
echo "----------------------------------------------------------------"
echo "Queue lengths:"

# Check common Celery queue names
for queue in celery default ward_flux celery@Flux; do
    LENGTH=$(docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN "$queue" 2>/dev/null)
    if [ -n "$LENGTH" ] && [ "$LENGTH" != "0" ]; then
        echo "  $queue: $LENGTH tasks"
    fi
done

echo ""
echo "----------------------------------------------------------------"
echo "Celery worker active/reserved tasks:"
docker exec wardops-worker-prod celery -A celery_app inspect active 2>/dev/null | head -20

echo ""
echo "----------------------------------------------------------------"
echo "Celery worker stats:"
docker exec wardops-worker-prod celery -A celery_app inspect stats 2>/dev/null | grep -E "total|pool" | head -10

echo ""
echo "----------------------------------------------------------------"
echo "Redis memory info:"
docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning INFO memory 2>/dev/null | grep -E "used_memory_human|used_memory_peak_human|maxmemory"

echo ""
echo "================================================================"
