#!/bin/bash

set -e

echo "=================================================================="
echo "  WARD OPS - FINAL DEPLOYMENT - Complete Cache Bypass"
echo "=================================================================="
echo ""
echo "This script will:"
echo "1. Build frontend OUTSIDE Docker to ensure fresh build"
echo "2. Copy pre-built assets into Docker image"
echo "3. Deploy to production"
echo ""

cd /home/wardops/ward-flux-credobank

echo "Step 1: Clean all caches..."
echo "=================================================================="
rm -rf frontend/dist frontend/.vite frontend/node_modules/.vite
docker system prune -f
docker rmi ward-flux-credobank_api:latest 2>/dev/null || true

echo ""
echo "Step 2: Build frontend on HOST machine (outside Docker)..."
echo "=================================================================="
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install --legacy-peer-deps
fi

# Clean build
echo "Building frontend with Vite..."
rm -rf dist .vite
npm run build

echo ""
echo "Frontend build complete! Checking hash..."
ls -lh dist/assets/ | grep index-

FRONTEND_HASH=$(ls dist/assets/ | grep "^index-.*\.js$")
echo "New frontend hash: $FRONTEND_HASH"

cd ..

echo ""
echo "Step 3: Create temporary Dockerfile that uses pre-built frontend..."
echo "=================================================================="

# Create a modified Dockerfile that skips frontend build
cat > Dockerfile.prebuilt <<'DOCKERFILE_END'
# WARD FLUX - Production with Pre-built Frontend
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 ward && \
    mkdir -p /app /data /logs && \
    chown -R ward:ward /app /data /logs

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libsnmp40 \
    curl \
    iputils-ping \
    mtr-tiny \
    traceroute \
    gcc \
    g++ \
    libpq-dev \
    libsnmp-dev \
    && chmod u+s /usr/bin/traceroute.db

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && chown ward:ward /app/docker-entrypoint.sh

# Copy application code
COPY --chown=ward:ward . .

# Copy PRE-BUILT frontend from host
COPY --chown=ward:ward frontend/dist /app/static_new

# Remove frontend source
RUN rm -rf /app/frontend

# Set environment variables
ENV PATH=/usr/local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/data/ward_flux.db \
    REDIS_URL=redis://redis:6379/0 \
    VICTORIA_URL=http://victoriametrics:8428

# Switch to non-root user
USER ward

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/api/v1/health || exit 1

# Default command
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
DOCKERFILE_END

echo "Created Dockerfile.prebuilt"

echo ""
echo "Step 4: Build Docker image with pre-built frontend..."
echo "=================================================================="
docker build \
  --no-cache \
  -f Dockerfile.prebuilt \
  -t ward-flux-credobank_api:latest \
  .

echo ""
echo "Step 5: Verify frontend in image..."
echo "=================================================================="
DOCKER_HASH=$(docker run --rm --entrypoint sh ward-flux-credobank_api:latest -c "ls /app/static_new/assets/ | grep '^index-.*\.js$'")
echo "Hash in Docker image: $DOCKER_HASH"

if [ "$DOCKER_HASH" = "$FRONTEND_HASH" ]; then
    echo "✅ SUCCESS! Hashes match - frontend was copied correctly"
else
    echo "❌ ERROR! Hash mismatch:"
    echo "  Built:  $FRONTEND_HASH"
    echo "  Docker: $DOCKER_HASH"
    exit 1
fi

echo ""
echo "Step 6: Stop old container and start new one..."
echo "=================================================================="
docker stop wardops-api-prod 2>/dev/null || true
docker rm wardops-api-prod 2>/dev/null || true

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
echo "Step 7: Verify deployment..."
echo "=================================================================="

# Check container is running
if docker ps | grep -q wardops-api-prod; then
    echo "✅ Container is running"
else
    echo "❌ Container failed to start!"
    docker logs wardops-api-prod --tail 50
    exit 1
fi

# Check API health
for i in {1..10}; do
    if curl -sf http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        break
    else
        if [ $i -eq 10 ]; then
            echo "⚠ API not responding after 10 attempts"
            docker logs wardops-api-prod --tail 30
        else
            echo "Attempt $i/10: Waiting for API..."
            sleep 3
        fi
    fi
done

echo ""
echo "=================================================================="
echo "  DEPLOYMENT COMPLETE!"
echo "=================================================================="
echo ""
echo "Frontend hash deployed: $FRONTEND_HASH"
echo ""
echo "CRITICAL: Clear browser cache before testing!"
echo ""
echo "  Windows/Linux: CTRL + SHIFT + R"
echo "  Mac: CMD + SHIFT + R"
echo ""
echo "Then verify:"
echo ""
echo "1. Open DevTools (F12) -> Network tab"
echo "2. Reload page and check JavaScript file loaded"
echo "   Should see: $FRONTEND_HASH"
echo ""
echo "3. Test delete button on Devices page"
echo "   - Click trash icon"
echo "   - Should see confirmation modal"
echo "   - Should see toast notification"
echo ""
echo "4. Check Monitor page"
echo "   - Only DOWN devices should appear"
echo "   - Downtime should match actual outage time"
echo ""
echo "=================================================================="

# Cleanup temporary Dockerfile
rm -f Dockerfile.prebuilt

echo ""
echo "Deployment script complete!"
