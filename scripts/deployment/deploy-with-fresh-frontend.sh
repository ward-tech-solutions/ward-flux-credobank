#!/bin/bash

set -e

echo "=================================================================="
echo "  Deploy with GUARANTEED Fresh Frontend Build"
echo "=================================================================="
echo ""

cd /home/wardops/ward-flux-credobank

echo "Step 1: Stop and remove API container..."
echo "=================================================================="
docker stop wardops-api-prod 2>/dev/null || true
docker rm wardops-api-prod 2>/dev/null || true

echo ""
echo "Step 2: Remove old images and cache..."
echo "=================================================================="
docker rmi ward-flux-credobank_api:latest 2>/dev/null || true
docker builder prune -f

echo ""
echo "Step 3: Build with BUILD_DATE cache buster..."
echo "=================================================================="
BUILD_DATE=$(date +%Y%m%d_%H%M%S)
echo "Build timestamp: $BUILD_DATE"
echo ""

# Build with BUILD_DATE arg to bust cache
docker build \
  --no-cache \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  -t ward-flux-credobank_api:latest \
  -f Dockerfile \
  . 2>&1 | tee /tmp/build_output.log

echo ""
echo "Step 4: Verify frontend build executed..."
echo "=================================================================="

if grep -q "npm run build" /tmp/build_output.log; then
    echo "✓ Frontend build step was executed"

    # Extract and show the build output
    echo ""
    echo "Build output preview:"
    grep -A 5 "npm run build" /tmp/build_output.log | head -10
else
    echo "⚠ WARNING: Could not find 'npm run build' in build log"
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
sleep 15

echo ""
echo "Step 6: Verify new frontend bundle..."
echo "=================================================================="

OLD_HASH="index-CWvAtuJb.js"
CURRENT_HASH=$(docker exec wardops-api-prod ls /app/static_new/assets/ | grep "^index-.*\.js$")

echo "Previous hash: $OLD_HASH"
echo "Current hash:  $CURRENT_HASH"
echo ""

if [ "$CURRENT_HASH" != "$OLD_HASH" ]; then
    echo "✅ SUCCESS! Frontend has been rebuilt with NEW hash!"
    echo ""
    echo "Frontend assets:"
    docker exec wardops-api-prod ls -lh /app/static_new/assets/
else
    echo "❌ FAILED: Frontend still has old hash!"
    echo ""
    echo "Possible reasons:"
    echo "1. Docker is using an old image from cache despite --no-cache"
    echo "2. The build didn't actually run npm build"
    echo ""
    echo "Checking image creation time..."
    docker images ward-flux-credobank_api:latest --format "Created: {{.CreatedSince}}"
fi

echo ""
echo "Step 7: Test API health..."
echo "=================================================================="

for i in {1..8}; do
    if curl -sf http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✓ API is healthy and responding"
        break
    else
        if [ $i -eq 8 ]; then
            echo "⚠ API not responding - check logs:"
            echo "   docker logs wardops-api-prod --tail 50"
        else
            echo "Attempt $i/8: Waiting for API..."
            sleep 3
        fi
    fi
done

echo ""
echo "=================================================================="
echo "  Deployment Complete!"
echo "=================================================================="
echo ""

if [ "$CURRENT_HASH" != "$OLD_HASH" ]; then
    echo "✅ FRONTEND SUCCESSFULLY REBUILT"
    echo ""
    echo "NEXT STEPS:"
    echo ""
    echo "1. Open browser and HARD REFRESH (CTRL+SHIFT+R or CMD+SHIFT+R)"
    echo ""
    echo "2. Open Devices page: http://10.30.25.39:5001/devices"
    echo ""
    echo "3. Open DevTools (F12) -> Network tab"
    echo "   Verify it loads: $CURRENT_HASH"
    echo ""
    echo "4. Test delete button:"
    echo "   - Click trash icon on a test device"
    echo "   - Should see confirmation modal"
    echo "   - Should see toast notification after delete"
    echo ""
else
    echo "⚠ FRONTEND NOT REBUILT - Further investigation needed"
    echo ""
    echo "Debug steps:"
    echo "1. Check build log: cat /tmp/build_output.log | less"
    echo "2. Check image age: docker images ward-flux-credobank_api"
    echo "3. Try complete system prune: docker system prune -af"
fi

echo ""
echo "=================================================================="
