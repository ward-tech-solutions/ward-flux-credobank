#!/bin/bash
# Rebuild frontend with latest changes

set -e

echo "🔨 Rebuilding API container with latest frontend fixes..."
echo "=========================================================="

# Stop API container
echo "⏹️  Stopping API container..."
docker-compose -f docker-compose.production-local.yml stop api

# Remove old container
echo "🗑️  Removing old container..."
docker-compose -f docker-compose.production-local.yml rm -f api

# Remove old image to force fresh build
echo "🗑️  Removing old image..."
OLD_IMAGE=$(docker images -q ward-flux-credobank_api)
if [ -n "$OLD_IMAGE" ]; then
    docker rmi -f $OLD_IMAGE
fi

# Build new image with NO cache
echo "🔨 Building fresh API image (no cache)..."
docker-compose -f docker-compose.production-local.yml build --no-cache api

# Start API container
echo "🚀 Starting API container..."
docker-compose -f docker-compose.production-local.yml up -d api

# Wait for API to be ready
echo "⏳ Waiting for API to start..."
sleep 15

# Show status
echo ""
echo "✅ Rebuild complete!"
echo ""
echo "📊 Container Status:"
docker ps -a | grep "wardops-api-prod"
echo ""
echo "🏥 API Health:"
curl -s http://localhost:5001/api/v1/health | jq .status
echo ""
echo "📋 Check the new image ID:"
docker images ward-flux-credobank_api | head -2
echo ""
echo "🌐 Frontend: http://10.30.25.39:5001/devices"
echo "🔄 Hard refresh browser: Ctrl+Shift+R"
