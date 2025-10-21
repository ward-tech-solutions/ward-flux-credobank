#!/bin/bash

set -e

echo "=================================================================="
echo "  WARD OPS - Proper Docker Build with Cache Invalidation"
echo "=================================================================="

cd /home/wardops/ward-flux-credobank

echo ""
echo "Step 1: Pull latest code..."
echo "=================================================================="
git pull origin main

echo ""
echo "Step 2: Stop and remove existing containers..."
echo "=================================================================="
docker stop wardops-api-prod wardops-worker-prod wardops-beat-prod 2>/dev/null || true
docker rm wardops-api-prod wardops-worker-prod wardops-beat-prod 2>/dev/null || true

echo ""
echo "Step 3: Remove old images..."
echo "=================================================================="
docker rmi ward-flux-credobank_api:latest ward-flux-credobank_celery-worker:latest ward-flux-credobank_celery-beat:latest 2>/dev/null || true

echo ""
echo "Step 4: Build with CACHE_BUST to force fresh frontend copy..."
echo "=================================================================="
CACHE_BUST=$(date +%s)
echo "Cache bust value: $CACHE_BUST"

docker-compose -f docker-compose.production-local.yml build \
  --no-cache \
  --build-arg CACHE_BUST="$CACHE_BUST" \
  api celery-worker celery-beat

echo ""
echo "Step 5: Verify frontend hash in built image..."
echo "=================================================================="
HASH=$(docker run --rm --entrypoint sh ward-flux-credobank_api:latest -c "ls /app/static_new/assets/ 2>/dev/null | grep '^index-.*\.js$'" || echo "ERROR")

if [ "$HASH" = "ERROR" ]; then
    echo "❌ Failed to read frontend assets from image"
    exit 1
fi

echo "Frontend bundle: $HASH"

if [ "$HASH" = "index-CWvAtuJb.js" ]; then
    echo ""
    echo "⚠️  WARNING: Frontend still has old hash!"
    echo "   This means the source files weren't updated in Docker"
    echo ""
    echo "   Checking git status..."
    git status
    echo ""
    echo "   Latest commits:"
    git log --oneline -5
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Frontend has NEW hash (not the old index-CWvAtuJb.js)"
fi

echo ""
echo "Step 6: Start containers..."
echo "=================================================================="
docker run -d --name wardops-api-prod --network ward-flux-credobank_default -p 5001:5001 \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e VICTORIA_URL='http://victoriametrics:8428' \
  -e DEFAULT_ADMIN_PASSWORD='admin123' \
  -e SECRET_KEY='local-prod-test-secret-key-change-me' \
  -e ENVIRONMENT='production' \
  -e MONITORING_MODE='snmp_only' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v api_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_api:latest

docker run -d --name wardops-worker-prod --network ward-flux-credobank_default \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e VICTORIA_URL='http://victoriametrics:8428' \
  -e SECRET_KEY='local-prod-test-secret-key-change-me' \
  -e ENVIRONMENT='production' \
  -e MONITORING_MODE='snmp_only' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v celery_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_celery-worker:latest \
  celery -A celery_app worker --loglevel=info --concurrency=100

docker run -d --name wardops-beat-prod --network ward-flux-credobank_default \
  -e DATABASE_URL='postgresql://ward_admin:ward_admin_password@postgres:5432/ward_ops' \
  -e REDIS_URL='redis://:redispass@redis:6379/0' \
  -e SECRET_KEY='local-prod-test-secret-key-change-me' \
  -e ENVIRONMENT='production' \
  -v /home/wardops/ward-flux-credobank/logs:/app/logs \
  -v beat_prod_data:/data \
  --restart unless-stopped \
  ward-flux-credobank_celery-beat:latest \
  celery -A celery_app beat --loglevel=info

echo ""
echo "Step 7: Wait for services to start..."
echo "=================================================================="
sleep 15

echo ""
echo "Step 8: Verify containers are running..."
echo "=================================================================="
docker ps --filter "name=wardops" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "Step 9: Check API health..."
echo "=================================================================="
for i in {1..10}; do
    if curl -sf http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        break
    else
        if [ $i -eq 10 ]; then
            echo "❌ API not responding"
            echo ""
            echo "Check logs:"
            echo "  docker logs wardops-api-prod --tail 50"
        else
            echo "Attempt $i/10..."
            sleep 3
        fi
    fi
done

echo ""
echo "=================================================================="
echo "  DEPLOYMENT COMPLETE"
echo "=================================================================="
echo ""
echo "Frontend bundle: $HASH"
echo ""
echo "⚠️  IMPORTANT: Clear your browser cache!"
echo ""
echo "  Windows/Linux: CTRL + SHIFT + R"
echo "  Mac: CMD + SHIFT + R"
echo ""
echo "Then test:"
echo ""
echo "1. Devices page - Delete button should work"
echo "2. Monitor page - Only DOWN devices should show"
echo "3. Check timezone fix in browser console"
echo ""
echo "=================================================================="
