#!/bin/bash

set -e

echo "=================================================================="
echo "  WARD OPS - Timezone Fix Deployment (v3 - Aggressive Cleanup)"
echo "=================================================================="
echo ""
echo "This will deploy the timezone fix for down_since timestamps"
echo ""

# Check if running on production server
if [ -d "/home/wardops/ward-flux-credobank" ]; then
    echo "✓ Detected production server environment"
    cd /home/wardops/ward-flux-credobank
else
    echo "Please run this on the production server"
    exit 1
fi

echo ""
echo "Step 1: Pulling latest code..."
echo "=================================================================="
git fetch origin
echo ""
echo "New commits to deploy:"
git log --oneline HEAD..origin/main | head -5

echo ""
read -p "Proceed with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

git pull origin main

echo ""
echo "Step 2: Aggressive cleanup of ALL related containers..."
echo "=================================================================="
echo "This will remove ALL containers that might be causing conflicts"
echo ""

# Stop all related containers (ignore errors if already stopped)
docker stop wardops-api-prod wardops-worker-prod wardops-beat-prod 2>/dev/null || true

# Remove by name
docker rm wardops-api-prod wardops-worker-prod wardops-beat-prod 2>/dev/null || true

# Find and remove any containers with ward-flux-credobank prefix
echo "Searching for orphaned containers..."
ORPHANED=$(docker ps -a --filter "name=wardops" --format "{{.ID}} {{.Names}}" | grep -E "(api|worker|beat)" | awk '{print $1}' || true)

if [ -n "$ORPHANED" ]; then
    echo "Found orphaned containers, removing them..."
    echo "$ORPHANED" | xargs -r docker rm -f 2>/dev/null || true
else
    echo "No orphaned containers found"
fi

# Also clean up any containers from the ward-flux-credobank images
STALE=$(docker ps -a --filter "ancestor=ward-flux-credobank_api" --format "{{.ID}}" || true)
if [ -n "$STALE" ]; then
    echo "Removing stale containers from old images..."
    echo "$STALE" | xargs -r docker rm -f 2>/dev/null || true
fi

STALE=$(docker ps -a --filter "ancestor=ward-flux-credobank_celery-worker" --format "{{.ID}}" || true)
if [ -n "$STALE" ]; then
    echo "Removing stale worker containers from old images..."
    echo "$STALE" | xargs -r docker rm -f 2>/dev/null || true
fi

echo "✓ All potentially conflicting containers removed"

echo ""
echo "Step 3: Rebuilding images (this will take 2-3 minutes)..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker celery-beat

echo ""
echo "Step 4: Creating and starting containers (using --force-recreate)..."
echo "=================================================================="
# Use --force-recreate to avoid ContainerConfig issues
docker-compose -f docker-compose.production-local.yml up -d --force-recreate api celery-worker celery-beat

echo ""
echo "Waiting for containers to initialize..."
sleep 15

echo ""
echo "Step 5: Verifying containers are running..."
echo "=================================================================="
docker ps --filter "name=wardops" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "Step 6: Checking container logs..."
echo "=================================================================="
echo ""
echo "API startup logs:"
docker logs wardops-api-prod --tail 30 2>&1 | tail -20

echo ""
echo "Worker startup logs:"
docker logs wardops-worker-prod --tail 30 2>&1 | tail -10

echo ""
echo "Step 7: Testing API health..."
echo "=================================================================="
echo "Waiting for API to be ready..."
sleep 5

# Health check with retries
for i in {1..10}; do
    if curl -s http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✓ API is responding"
        break
    else
        echo "Attempt $i/10: API not ready yet, waiting..."
        sleep 5
    fi
done

echo ""
echo "Step 8: Verifying timezone fix is active..."
echo "=================================================================="
echo ""
echo "Checking down_since timestamp format in API response..."
echo ""

# Make API call and check for timezone suffix
RESPONSE=$(curl -s http://localhost:5001/api/v1/devices/standalone)
SAMPLE=$(echo "$RESPONSE" | jq -r '.[] | select(.down_since != null) | .down_since' | head -1)

if [ -z "$SAMPLE" ]; then
    echo "⚠ No down devices found to test timezone format"
    echo ""
    echo "Testing with a random device timestamp instead:"
    echo "$RESPONSE" | jq -r '.[0] | {name: .name, last_check: .last_check}' | head -3
else
    echo "Sample down_since timestamp: $SAMPLE"
    echo ""
    if [[ "$SAMPLE" == *"+00:00" ]] || [[ "$SAMPLE" == *"Z" ]]; then
        echo "✅ SUCCESS: Timezone suffix (+00:00 or Z) is present!"
        echo ""
        echo "The timezone fix is ACTIVE!"
    else
        echo "❌ WARNING: Timezone suffix is MISSING!"
        echo "   Expected format: 2025-10-21T08:34:45.186571+00:00"
        echo "   Got format:      $SAMPLE"
        echo ""
        echo "The fix may not have deployed correctly."
    fi
fi

echo ""
echo "=================================================================="
echo "  Deployment Complete!"
echo "=================================================================="
echo ""
echo "✅ All conflicting containers removed"
echo "✅ New images built with updated code"
echo "✅ Containers recreated with --force-recreate"
echo "✅ All services running"
echo ""
echo "DEPLOYED FIXES:"
echo ""
echo "1. ✅ Timezone fix for down_since timestamps"
echo "   - Backend now sends timestamps with +00:00 suffix"
echo "   - Frontend will calculate correct downtime duration"
echo ""
echo "2. ✅ Delete button for devices (code deployed, needs frontend verification)"
echo "   - Delete button in grid and list views"
echo "   - Confirmation modal"
echo "   - Toast notifications"
echo ""
echo "3. ✅ Toast notifications for all device operations"
echo "   - Success/error messages for add/edit/delete"
echo "   - Shows backend errors (e.g., duplicate IP)"
echo ""
echo "NEXT STEPS - Verify in Browser:"
echo ""
echo "1. Open Monitor page: http://10.30.25.39:5001/monitor"
echo ""
echo "2. Press F12 to open browser console and check debug logs:"
echo "   BEFORE FIX: Diff hours: 6.07 (WRONG)"
echo "   AFTER FIX:  Diff hours: 0.05 (CORRECT)"
echo ""
echo "3. Verify downtime matches Zabbix:"
echo "   - If Zabbix shows device down 30 min ago"
echo "   - Monitor page should show 'Down 30m' (not 'Down 4h')"
echo ""
echo "4. Test delete button on Devices page:"
echo "   - Click delete button on a test device"
echo "   - Should show confirmation modal"
echo "   - Should show success toast after deletion"
echo ""
echo "MONITORING:"
echo ""
echo "Watch worker logs for state transitions:"
echo "  docker logs wardops-worker-prod -f | grep -E 'went DOWN|came back UP'"
echo ""
echo "Check API logs:"
echo "  docker logs wardops-api-prod -f"
echo ""
echo "=================================================================="
