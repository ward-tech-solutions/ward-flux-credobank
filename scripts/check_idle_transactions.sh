#!/bin/bash
# Monitor and kill idle database transactions
# Run this as a cron job every 5 minutes to prevent connection pool exhaustion

set -e

echo "=== Database Connection Health Check ==="
echo "Time: $(date)"
echo ""

# Check connection counts by state
echo "1. Connection counts by state:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state
ORDER BY count DESC;"

echo ""

# Check for long-running idle transactions
echo "2. Idle transactions (> 30 seconds):"
IDLE_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT count(*)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND now() - query_start > interval '30 seconds';" | tr -d ' ')

echo "Found: $IDLE_COUNT idle transactions"
echo ""

# If there are idle transactions older than 1 minute, kill them
if [ "$IDLE_COUNT" -gt 0 ]; then
    echo "3. Checking for transactions > 1 minute (will auto-kill):"

    KILL_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
    SELECT count(*)
    FROM pg_stat_activity
    WHERE state = 'idle in transaction'
    AND now() - query_start > interval '1 minute';" | tr -d ' ')

    if [ "$KILL_COUNT" -gt 0 ]; then
        echo "⚠️  Killing $KILL_COUNT stuck transactions..."

        docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE state = 'idle in transaction'
        AND now() - query_start > interval '1 minute';" > /dev/null

        echo "✅ Killed $KILL_COUNT stuck transactions"

        # Log to file
        echo "$(date): Killed $KILL_COUNT idle transactions" >> /var/log/wardops-db-cleanup.log
    else
        echo "✅ No transactions older than 1 minute"
    fi
else
    echo "✅ No idle transactions detected"
fi

echo ""
echo "4. Current connection pool usage:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT count(*) as total_connections
FROM pg_stat_activity;"

echo ""
echo "=== Check Complete ==="
