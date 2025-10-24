#!/bin/bash

# Deploy ONLY the Timezone Fix (commit ad62423)
# Fixes downtime calculation showing wrong duration
# Adds 'Z' suffix to timestamps so JavaScript parses as UTC

set -e

echo "========================================="
echo "Deploying Timezone Fix ONLY"
echo "========================================="
echo ""
echo "Fix: Append 'Z' to down_since timestamps"
echo "File: routers/devices_standalone.py line 187"
echo "Commit: ad62423"
echo ""

# Step 1: Pull latest code
echo "[1/4] Pulling latest code..."
git pull origin main
echo "✅ Done"
echo ""

# Step 2: Rebuild API container
echo "[2/4] Rebuilding API container..."
echo "(This takes 2-3 minutes...)"
docker-compose -f docker-compose.production-priority-queues.yml build api
echo "✅ Done"
echo ""

# Step 3: Restart API container
echo "[3/4] Restarting API container..."
docker-compose -f docker-compose.production-priority-queues.yml stop api
sleep 5
docker-compose -f docker-compose.production-priority-queues.yml up -d api
echo "Waiting 15 seconds for startup..."
sleep 15
echo "✅ Done"
echo ""

# Step 4: Clear Redis cache
echo "[4/4] Clearing Redis cache..."
docker exec wardops-redis-prod redis-cli -a redispass FLUSHDB > /dev/null 2>&1
echo "✅ Done"
echo ""

echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Timezone fix deployed:"
echo "  - Timestamps now include 'Z' suffix (UTC indicator)"
echo "  - JavaScript will parse as UTC instead of local time"
echo "  - Downtime calculation should be accurate"
echo ""
echo "Verify deployment:"
echo "  bash check-timezone-fix.sh"
echo ""
echo "Expected result:"
echo "  ✅ TIMEZONE FIX DEPLOYED - timestamp has Z suffix"
echo "  down_since: 2025-10-24T16:03:52.052638Z"
echo ""
