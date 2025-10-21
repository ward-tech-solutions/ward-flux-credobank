#!/bin/bash

set -e

echo "=================================================================="
echo "  Force Frontend Rebuild - Complete Cache Bust"
echo "=================================================================="
echo ""

cd /home/wardops/ward-flux-credobank

echo "Step 1: Removing all Docker build cache..."
echo "=================================================================="
# Remove the specific images to force rebuild
docker rmi ward-flux-credobank_api:latest 2>/dev/null || true
docker rmi $(docker images -q --filter "label=stage=frontend-builder") 2>/dev/null || true

# Prune build cache
docker builder prune -f

echo "✓ Build cache cleared"

echo ""
echo "Step 2: Stop API container..."
echo "=================================================================="
docker stop wardops-api-prod
docker rm wardops-api-prod

echo ""
echo "Step 3: Building with NO CACHE (this will take 3-4 minutes)..."
echo "=================================================================="
echo "Building frontend from scratch..."

# Build with additional flags to ensure no caching
DOCKER_BUILDKIT=1 docker-compose -f docker-compose.production-local.yml build \
  --no-cache \
  --pull \
  --progress=plain \
  api 2>&1 | tee /tmp/build.log

echo ""
echo "Step 4: Verify frontend was rebuilt..."
echo "=================================================================="

# Check if build log shows frontend rebuild
if grep -q "npm run build" /tmp/build.log; then
    echo "✓ Frontend build step executed"
else
    echo "⚠ WARNING: Frontend build step may have been skipped"
fi

echo ""
echo "Step 5: Start new API container..."
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

echo ""
echo "Waiting for API to start..."
sleep 10

echo ""
echo "Step 6: Verify new frontend files..."
echo "=================================================================="

echo "Frontend assets in container:"
docker exec wardops-api-prod ls -la /app/static_new/assets/

echo ""
echo "Checking for NEW JavaScript bundle hash..."

NEW_HASH=$(docker exec wardops-api-prod ls /app/static_new/assets/ | grep "^index-" | grep ".js$")
echo "Current bundle: $NEW_HASH"

if [ "$NEW_HASH" = "index-CWvAtuJb.js" ]; then
    echo ""
    echo "❌ WARNING: Frontend still has OLD hash!"
    echo "   The frontend was NOT rebuilt"
    echo ""
    echo "This means Docker's cache is very aggressive."
    echo "Trying nuclear option..."
    echo ""

    # Nuclear option: remove ALL images and build from absolute scratch
    docker stop wardops-api-prod
    docker rm wardops-api-prod
    docker rmi -f $(docker images -q ward-flux-credobank_api)
    docker system prune -af --volumes=false

    echo "Building with absolutely no cache..."
    DOCKER_BUILDKIT=0 docker build --no-cache -t ward-flux-credobank_api:latest .

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

    sleep 10
    NEW_HASH=$(docker exec wardops-api-prod ls /app/static_new/assets/ | grep "^index-" | grep ".js$")
    echo "After nuclear rebuild: $NEW_HASH"
fi

if [ "$NEW_HASH" != "index-CWvAtuJb.js" ]; then
    echo ""
    echo "✅ SUCCESS! Frontend has NEW hash: $NEW_HASH"
    echo ""
else
    echo ""
    echo "❌ FAILED: Frontend still has old hash"
    echo ""
fi

echo ""
echo "Step 7: Test API..."
echo "=================================================================="

for i in {1..5}; do
    if curl -sf http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✓ API is responding"
        break
    else
        echo "Attempt $i/5: Waiting for API..."
        sleep 3
    fi
done

echo ""
echo "=================================================================="
echo "  Rebuild Complete!"
echo "=================================================================="
echo ""
echo "VERIFICATION:"
echo ""
echo "1. Clear browser cache (CTRL+SHIFT+R or CMD+SHIFT+R)"
echo "2. Open Devices page: http://10.30.25.39:5001/devices"
echo "3. Open browser console (F12) -> Network tab"
echo "4. Refresh page and check what JS file loads:"
echo "   - OLD: index-CWvAtuJb.js ❌"
echo "   - NEW: index-XXXXXXXX.js ✅ (different hash)"
echo ""
echo "5. Click delete button on a test device"
echo "6. Should see confirmation modal and toast notification"
echo ""
echo "=================================================================="
