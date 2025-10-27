#!/bin/bash

# ================================================================
# WARD OPS - Diagnose Deployment Issues
# ================================================================

echo "=========================================="
echo "WARD OPS - Deployment Diagnostics"
echo "=========================================="
echo ""

echo "1. Container Status:"
echo "--------------------------------------"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep wardops
echo ""

echo "2. Checking API Health:"
echo "--------------------------------------"
echo "Waiting 5 seconds for API to be ready..."
sleep 5

# Try to hit the health endpoint
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/health 2>/dev/null || echo "failed")
echo "API Health Endpoint: HTTP $API_HEALTH"

if [ "$API_HEALTH" != "200" ]; then
    echo ""
    echo "⚠️  API not responding. Checking logs..."
    echo ""
    echo "API Logs (last 40 lines):"
    docker logs --tail=40 wardops-api-prod
fi

echo ""
echo "3. Checking Database Migration:"
echo "--------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops << 'EOF'
-- Check if down_since column exists
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'standalone_devices'
            AND column_name = 'down_since'
        ) THEN '✅ down_since column EXISTS'
        ELSE '❌ down_since column MISSING - migration needed!'
    END AS migration_status;

-- Show column details if it exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'standalone_devices'
AND column_name = 'down_since';
EOF

echo ""
echo "4. Celery Worker Status:"
echo "--------------------------------------"
WORKER_LOGS=$(docker logs --tail=20 wardops-worker-prod 2>&1)
if echo "$WORKER_LOGS" | grep -q "ready"; then
    echo "✅ Celery worker is ready"
else
    echo "⚠️  Celery worker may have issues. Recent logs:"
    docker logs --tail=20 wardops-worker-prod
fi

echo ""
echo "5. Celery Beat Status:"
echo "--------------------------------------"
BEAT_LOGS=$(docker logs --tail=20 wardops-beat-prod 2>&1)
if echo "$BEAT_LOGS" | grep -q "beat"; then
    echo "✅ Celery beat is running"
else
    echo "⚠️  Celery beat may have issues. Recent logs:"
    docker logs --tail=20 wardops-beat-prod
fi

echo ""
echo "6. Database Connection Test:"
echo "--------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "SELECT COUNT(*) as device_count FROM standalone_devices;"

echo ""
echo "7. Redis Connection Test:"
echo "--------------------------------------"
docker exec wardops-redis-prod redis-cli -a redispass ping 2>/dev/null && echo "✅ Redis is responding" || echo "❌ Redis connection failed"

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "If you see errors above, common fixes:"
echo ""
echo "1. Migration not applied:"
echo "   Run: docker exec -i wardops-postgres-prod psql -U ward_admin -d ward_ops < migrations/add_down_since_column.sql"
echo ""
echo "2. Containers unhealthy but logs look good:"
echo "   Wait 2-3 more minutes for health checks to pass"
echo ""
echo "3. API errors in logs:"
echo "   docker-compose -f docker-compose.production-local.yml restart api"
echo ""
echo "4. Worker errors:"
echo "   docker-compose -f docker-compose.production-local.yml restart celery-worker"
echo ""
echo "For detailed logs of any service:"
echo "   docker logs -f wardops-<service>-prod"
echo ""
