#!/bin/bash

echo "================================================================"
echo "  REDIS QUEUE GROWTH MONITOR"
echo "================================================================"
echo ""
echo "Monitoring queue for 2 minutes (every 10 seconds)..."
echo "Press Ctrl+C to stop"
echo ""
echo "Time                    | Queue Size | Change"
echo "----------------------------------------------------------------"

PREV_SIZE=0
for i in {1..12}; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    QUEUE_SIZE=$(docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery 2>/dev/null)

    if [ $i -eq 1 ]; then
        CHANGE="(baseline)"
    else
        DIFF=$((QUEUE_SIZE - PREV_SIZE))
        if [ $DIFF -gt 0 ]; then
            CHANGE="+$DIFF"
        else
            CHANGE="$DIFF"
        fi
    fi

    printf "%-24s| %-11s| %s\n" "$TIMESTAMP" "$QUEUE_SIZE" "$CHANGE"

    PREV_SIZE=$QUEUE_SIZE

    if [ $i -lt 12 ]; then
        sleep 10
    fi
done

echo ""
echo "================================================================"
echo "Summary:"
FINAL_SIZE=$(docker exec wardops-redis-prod redis-cli -a redispass --no-auth-warning LLEN celery 2>/dev/null)
echo "  Final queue size: $FINAL_SIZE tasks"
echo "  Growth rate: $((FINAL_SIZE / 2)) tasks/minute (approx)"
echo ""

if [ $FINAL_SIZE -lt 100 ]; then
    echo "✓ Queue growth is NORMAL - system is healthy"
elif [ $FINAL_SIZE -lt 1000 ]; then
    echo "⚠ Queue growing slowly - monitor for a few hours"
else
    echo "✗ Queue growing rapidly - optimization needed!"
fi
echo "================================================================"
