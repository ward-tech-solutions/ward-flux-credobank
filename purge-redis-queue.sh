#!/bin/bash

# WARD OPS CredoBank - Purge Redis Queue
# WARNING: This will delete all queued tasks

echo "================================================================"
echo "  REDIS QUEUE PURGE SCRIPT"
echo "================================================================"
echo ""
echo "⚠️  WARNING: This will delete all queued Celery tasks!"
echo ""
echo "Current queue status:"
QUEUE_SIZE=$(docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery 2>/dev/null)
echo "  Tasks queued: $QUEUE_SIZE"
echo ""

if [ "$QUEUE_SIZE" -eq 0 ]; then
    echo "✓ Queue is already empty. Nothing to purge."
    exit 0
fi

read -p "Are you sure you want to purge the queue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Purge cancelled."
    exit 0
fi

echo ""
echo "Purging queue..."

# Delete the celery queue
docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning DEL celery 2>/dev/null

NEW_SIZE=$(docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery 2>/dev/null)

echo ""
echo "================================================================"
echo "  PURGE COMPLETE"
echo "================================================================"
echo "  Before: $QUEUE_SIZE tasks"
echo "  After: $NEW_SIZE tasks"
echo ""
echo "✓ Queue purged successfully"
echo ""
echo "IMPORTANT: New tasks will be created by beat scheduler:"
echo "  - Every 30s: ping_all_devices (876 tasks)"
echo "  - Every 60s: poll_all_devices_snmp (N tasks)"
echo ""
echo "Monitor queue with:"
echo "  docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery"
echo ""
