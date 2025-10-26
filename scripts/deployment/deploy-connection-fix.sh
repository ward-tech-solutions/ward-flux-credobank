#!/bin/bash
set -e

echo "🚀 Deploying Database Connection Pool Fix"
echo "=========================================="
echo ""

# Kill current idle transactions first
echo "1. Killing existing idle transactions..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND now() - query_start > interval '30 seconds';" | grep -c "t" || echo "0"

echo "✅ Cleared stuck connections"
echo ""

# Pull latest code
echo "2. Pulling latest code..."
git stash save "Auto-stash before connection fix $(date)" 2>/dev/null || true
git fetch origin
git pull origin main
echo "✅ Code updated"
echo ""

# Rebuild containers with new code
echo "3. Rebuilding containers..."
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker celery-beat
echo "✅ Containers rebuilt"
echo ""

# Restart services
echo "4. Restarting services..."
docker-compose -f docker-compose.production-local.yml restart api celery-worker celery-beat
echo "✅ Services restarted"
echo ""

# Wait for services to be ready
echo "5. Waiting for services to start..."
sleep 15
echo ""

# Check service health
echo "6. Checking service health..."
docker-compose -f docker-compose.production-local.yml ps
echo ""

# Test API performance
echo "7. Testing API performance..."
echo "Running 3 consecutive tests:"
for i in {1..3}; do
  echo -n "  Test $i: "
  START=$(date +%s.%N)
  curl -s http://localhost:5001/api/v1/devices > /dev/null
  END=$(date +%s.%N)
  DURATION=$(echo "$END - $START" | bc)
  echo "${DURATION}s"
done
echo ""

# Check database connections
echo "8. Checking database connection health..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT state, count(*) as connections
FROM pg_stat_activity
GROUP BY state
ORDER BY connections DESC;"
echo ""

# Monitor for 30 seconds
echo "9. Monitoring connections for 30 seconds..."
echo "   (Should stay stable, no 'idle in transaction' accumulation)"
sleep 30

docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT state, count(*) as connections
FROM pg_stat_activity
WHERE state = 'idle in transaction'
GROUP BY state;"

IDLE_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "
SELECT count(*)
FROM pg_stat_activity
WHERE state = 'idle in transaction';" | tr -d ' ')

echo ""
if [ "$IDLE_COUNT" -gt "10" ]; then
    echo "⚠️  WARNING: Still accumulating idle transactions ($IDLE_COUNT found)"
    echo "   The fix may not be working correctly."
    echo "   Check logs: docker logs wardops-worker-prod --tail 50"
else
    echo "✅ SUCCESS: Idle transactions under control ($IDLE_COUNT found)"
    echo "   System is healthy!"
fi
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Monitor connections: watch -n 5 'docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c \"SELECT state, count(*) FROM pg_stat_activity GROUP BY state;\"'"
echo "2. Check worker logs: docker logs wardops-worker-prod -f"
echo "3. Test browser performance: Open Monitor page and check Network tab"
echo ""
echo "To manually kill idle transactions:"
echo "docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND now() - query_start > interval '1 minute';\""
