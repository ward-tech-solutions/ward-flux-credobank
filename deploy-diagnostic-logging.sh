#!/bin/bash

echo "🚀 Deploying Diagnostic Logging for Cache Clearing"
echo "=================================================="
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
echo "🔨 Step 2: Rebuild monitoring worker container..."
docker compose -f docker-compose.production-priority-queues.yml build celery-worker-monitoring
if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "🔄 Step 3: Restart monitoring worker..."
docker compose -f docker-compose.production-priority-queues.yml up -d celery-worker-monitoring
if [ $? -ne 0 ]; then
    echo "❌ Restart failed"
    exit 1
fi

echo ""
echo "⏳ Waiting 10 seconds for worker to start..."
sleep 10

echo ""
echo "✅ Step 4: Verify worker is running..."
docker ps | grep worker-monitoring

echo ""
echo "📊 Step 5: Check worker health..."
docker inspect wardops-worker-monitoring-prod --format='{{.State.Health.Status}}'

echo ""
echo "🎯 Step 6: Monitor for cache clearing messages (next 60 seconds)..."
echo "Watching for: Status change detected, Cleared cache, Cache was empty"
echo ""
timeout 60 docker logs -f wardops-worker-monitoring-prod 2>&1 | grep --line-buffered -E "Status change detected|Cleared.*cache|cache was empty|went DOWN|RECOVERED" || true

echo ""
echo "=================================================="
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Continue monitoring with:"
echo "   docker logs -f wardops-worker-monitoring-prod 2>&1 | grep -E 'Status change|Cleared|went DOWN|RECOVERED'"
echo ""
echo "2. Wait for next device status change (DOWN/UP)"
echo ""
echo "3. You should now see one of these messages:"
echo "   - 🔔 Status change detected in batch - clearing device list cache"
echo "   - 🗑️  Cleared X device list cache entries after status change"
echo "   - 🗑️  Cache clearing triggered but no cache keys found"
echo ""
