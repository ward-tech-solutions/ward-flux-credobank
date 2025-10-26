#!/bin/bash

# Deploy Timezone Fix - Manual Container Management
# Handles docker-compose ContainerConfig errors by manually managing containers

set -e

echo "========================================="
echo "Deploying Timezone Fix (Manual Method)"
echo "========================================="
echo ""

# Step 1: Pull latest code
echo "[1/5] Pulling latest code..."
git pull origin main
echo "✅ Done"
echo ""

# Step 2: Rebuild API container
echo "[2/5] Rebuilding API image..."
docker-compose -f docker-compose.production-priority-queues.yml build api
echo "✅ Done"
echo ""

# Step 3: Stop old container
echo "[3/5] Stopping old API container..."
docker stop wardops-api-prod 2>/dev/null || echo "Container already stopped"
echo "✅ Done"
echo ""

# Step 4: Remove old container (fixes ContainerConfig error)
echo "[4/5] Removing old API container..."
docker rm wardops-api-prod 2>/dev/null || echo "Container already removed"
echo "✅ Done"
echo ""

# Step 5: Start new container
echo "[5/5] Starting new API container..."
docker-compose -f docker-compose.production-priority-queues.yml up -d api

echo "Waiting 15 seconds for startup..."
sleep 15
echo "✅ Done"
echo ""

# Clear Redis cache
echo "Clearing Redis cache..."
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB > /dev/null 2>&1
echo "✅ Done"
echo ""

# Verify
echo "========================================="
echo "Verifying Deployment"
echo "========================================="
echo ""

# Check container status
echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(api|NAME)"
echo ""

# Check health
echo "Checking API health..."
sleep 5
if curl -sf http://localhost:5001/api/v1/health > /dev/null 2>&1; then
    echo "✅ API is healthy"
else
    echo "⚠️  API health check failed, checking logs..."
    docker logs wardops-api-prod --tail 20
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Run verification:"
echo "  bash check-timezone-fix.sh"
echo ""
