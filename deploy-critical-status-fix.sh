#!/bin/bash

echo "🚨 CRITICAL FIX: Device Status Bug"
echo "=================================================="
echo "This fixes the issue where devices show as UP when they're actually DOWN"
echo ""

# Navigate to project directory
cd /home/wardops/ward-flux-credobank

echo "📥 Step 1: Pull latest code from GitHub..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Git pull failed"
    exit 1
fi

echo ""
echo "🔨 Step 2: Rebuild API container..."
docker-compose -f docker-compose.production-priority-queues.yml build api
if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "🔄 Step 3: Restart API container..."
docker-compose -f docker-compose.production-priority-queues.yml up -d api
if [ $? -ne 0 ]; then
    echo "❌ Restart failed"
    exit 1
fi

echo ""
echo "⏳ Waiting 10 seconds for API to start..."
sleep 10

echo ""
echo "✅ Step 4: Verify API is running..."
docker ps | grep wardops-api-prod
docker inspect wardops-api-prod --format='{{.State.Health.Status}}'

echo ""
echo "🧪 Step 5: Test the fix..."
echo "Querying device 10.195.110.51 (PING-Call) which is DOWN in database..."
curl -s http://localhost:5001/api/v1/devices | jq '.[] | select(.ip == "10.195.110.51") | {name, ip, ping_status, available, down_since}' || echo "jq not installed, skipping test"

echo ""
echo "=================================================="
echo "✅ Deployment complete!"
echo ""
echo "What changed:"
echo "- API now uses device.down_since as source of truth for device status"
echo "- No longer relies on stale PingResult.is_reachable data"
echo "- Device status will update within 10 seconds (ping interval)"
echo ""
echo "Next steps:"
echo "1. Refresh the UI (Ctrl+F5 or Cmd+Shift+R)"
echo "2. Check if devices showing correctly"
echo "3. Verify DOWN devices show as DOWN (red)"
echo "4. Verify UP devices show as UP (green)"
echo ""
echo "Test device: PING-Call (10.195.110.51) should show as DOWN"
echo ""
