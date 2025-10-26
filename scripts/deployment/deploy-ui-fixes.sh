#!/bin/bash

# Deploy UI Fixes to Credobank Production
# This script deploys three UI-related fixes:
# 1. Device status display bug (commit e123567)
# 2. Settings page error messages (commit d7b252b)
# 3. Timezone bug in downtime calculation (commit ad62423)

set -e  # Exit on any error

echo "========================================="
echo "Deploying UI Fixes to Credobank"
echo "========================================="
echo ""

# Step 1: Pull latest code
echo "[1/5] Pulling latest code from origin..."
git pull origin main
echo "✅ Code updated"
echo ""

# Step 2: Show recent commits being deployed
echo "[2/5] Recent commits being deployed:"
git log --oneline -5 | grep -E "(e123567|d7b252b|ad62423)" || git log --oneline -5
echo ""

# Step 3: Rebuild API container (includes frontend build)
echo "[3/5] Rebuilding API container with frontend..."
echo "This will take 2-3 minutes (building React frontend + Python backend)..."
docker-compose -f docker-compose.production-priority-queues.yml build api
echo "✅ API container rebuilt"
echo ""

# Step 4: Restart API container
echo "[4/5] Restarting API container..."
docker-compose -f docker-compose.production-priority-queues.yml stop api

# Find and remove old stopped API container
OLD_CONTAINER=$(docker ps -a | grep "api" | grep "Exited" | awk '{print $1}' | head -1)
if [ ! -z "$OLD_CONTAINER" ]; then
    echo "Removing old container: $OLD_CONTAINER"
    docker rm $OLD_CONTAINER
fi

docker-compose -f docker-compose.production-priority-queues.yml up -d api

echo "Waiting 15 seconds for API to start..."
sleep 15
echo "✅ API container restarted"
echo ""

# Step 5: Verify and clear cache
echo "[5/5] Verifying deployment..."

# Check container is running
if docker ps | grep -q "api"; then
    echo "✅ API container is running"
else
    echo "❌ API container is NOT running!"
    docker ps -a | grep api
    exit 1
fi

# Check health endpoint
echo "Checking API health..."
if curl -sf http://localhost:5001/api/v1/health > /dev/null 2>&1; then
    echo "✅ API health check passed"
else
    echo "⚠️  API health check failed, but container is running"
    echo "Check logs: docker logs <api_container_name>"
fi

# Clear Redis cache
echo ""
echo "Clearing Redis cache for fresh data..."
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB > /dev/null 2>&1
echo "✅ Redis cache cleared"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Three UI fixes deployed:"
echo ""
echo "1. ✅ Device Status Display Fix"
echo "   - Fixed: Devices showing UP when actually DOWN"
echo "   - Changed: API now uses down_since field (source of truth)"
echo "   - File: routers/devices_standalone.py"
echo "   - Commit: e123567"
echo ""
echo "2. ✅ Settings Page Error Messages"
echo "   - Fixed: No error shown for duplicate username/email"
echo "   - Changed: Added error handling to Settings user modals"
echo "   - File: frontend/src/pages/Settings.tsx"
echo "   - Commit: d7b252b"
echo ""
echo "3. ✅ Timezone Fix for Downtime"
echo "   - Fixed: down_since timestamps missing 'Z' suffix"
echo "   - Changed: Append 'Z' to indicate UTC timezone"
echo "   - File: routers/devices_standalone.py"
echo "   - Commit: ad62423"
echo ""
echo "========================================="
echo "Testing Instructions"
echo "========================================="
echo ""
echo "Test 1: Device Status (Fix #1)"
echo "  1. Open: http://10.30.25.46:5001/monitor"
echo "  2. Search for: 10.195.5.17 (RuckusAP-AP)"
echo "  3. Expected: RED 'Down' indicator (not green)"
echo "  4. Click device to view details"
echo "  5. Expected: Both grid and detail view show 'Down'"
echo ""
echo "Test 2: Settings Error Messages (Fix #2)"
echo "  1. Open: http://10.30.25.46:5001/settings"
echo "  2. Scroll to 'User Management' section"
echo "  3. Click 'Add New User'"
echo "  4. Enter username: 'admin' (existing user)"
echo "  5. Fill other fields, click 'Add User'"
echo "  6. Expected: RED error box with 'Username already registered'"
echo "  7. Click X button"
echo "  8. Expected: Error disappears"
echo ""
echo "Test 3: Downtime Calculation (Fix #3)"
echo "  1. Open: http://10.30.25.46:5001/monitor"
echo "  2. Find a DOWN device (red indicator)"
echo "  3. Check downtime shown (e.g., '37m' or '2h 15m')"
echo "  4. Open browser DevTools (F12 → Console)"
echo "  5. Look for debug logs:"
echo "     [DeviceName] down_since: 2025-10-24T16:03:52.052638Z"
echo "     Date: 2025-10-24T16:03:52.052Z"
echo "     Diff hours: 0.62"
echo "  6. Refresh page (F5)"
echo "  7. Expected: Downtime doesn't reset, increases by ~1 minute"
echo ""
echo "If Test 3 still shows wrong downtime:"
echo "  - Check browser console for the debug logs"
echo "  - Note the 'Diff hours' value"
echo "  - Compare with database:"
echo "    docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c \\"
echo "      \"SELECT name, ip, down_since, NOW() as current_time FROM standalone_devices WHERE down_since IS NOT NULL;\""
echo ""
echo "Container Logs (if needed):"
echo "  docker logs <api_container_name> --tail 50"
echo ""
