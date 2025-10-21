#!/bin/bash

set -e

echo "=================================================================="
echo "  WARD OPS - Timezone Fix Deployment (v2 - Fixed)"
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
echo "Step 2: Stopping and REMOVING old containers..."
echo "=================================================================="
echo "This avoids the ContainerConfig error"

# Stop containers
docker stop wardops-api-prod wardops-worker-prod 2>/dev/null || true

# Remove containers completely
docker rm wardops-api-prod wardops-worker-prod 2>/dev/null || true

echo "✓ Old containers removed"

echo ""
echo "Step 3: Rebuilding images (this will take 2-3 minutes)..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker

echo ""
echo "Step 4: Creating and starting NEW containers..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml up -d api celery-worker

echo ""
echo "Waiting for containers to initialize..."
sleep 15

echo ""
echo "Step 5: Verifying containers are running..."
echo "=================================================================="
docker ps | grep -E 'wardops-(api|worker)-prod'

echo ""
echo "Step 6: Checking container logs..."
echo "=================================================================="
echo ""
echo "API startup logs:"
docker logs wardops-api-prod --tail 20

echo ""
echo "Step 7: Testing API health..."
echo "=================================================================="
echo "Waiting for API to be ready..."
sleep 5

# Health check with retries
for i in {1..6}; do
    if curl -s http://localhost:5001/api/v1/health > /dev/null 2>&1; then
        echo "✓ API is responding"
        break
    else
        echo "Attempt $i/6: API not ready yet, waiting..."
        sleep 5
    fi
done

echo ""
echo "Step 8: Verifying timezone fix is active..."
echo "=================================================================="
echo ""
echo "Checking down_since timestamp format..."
echo ""

# Make API call and check for timezone suffix
SAMPLE=$(curl -s http://localhost:5001/api/v1/devices/standalone | jq -r '.[] | select(.down_since != null) | .down_since' | head -1)

if [ -z "$SAMPLE" ]; then
    echo "⚠ No down devices found to test timezone format"
    echo "  (This is OK - it means all devices are UP)"
else
    echo "Sample down_since timestamp: $SAMPLE"
    echo ""
    if [[ "$SAMPLE" == *"+00:00" ]] || [[ "$SAMPLE" == *"Z" ]]; then
        echo "✅ SUCCESS: Timezone suffix (+00:00 or Z) is present!"
    else
        echo "❌ WARNING: Timezone suffix is MISSING!"
        echo "   Expected format: 2025-10-21T08:34:45.186571+00:00"
        echo "   Got format:      $SAMPLE"
    fi
fi

echo ""
echo "=================================================================="
echo "  Deployment Complete!"
echo "=================================================================="
echo ""
echo "✅ Old containers removed"
echo "✅ New images built with updated code"
echo "✅ Containers recreated and running"
echo ""
echo "NEXT STEPS - Verify in Browser:"
echo ""
echo "1. Open Monitor page: http://10.30.25.39:5001/monitor"
echo ""
echo "2. Press F12 to open browser console"
echo ""
echo "3. Check the debug logs for down devices:"
echo "   - down_since should show: 2025-10-21T08:34:45.186571+00:00"
echo "   - Diff hours should be SMALL (< 1.0 for recent outages)"
echo ""
echo "4. Verify downtime calculation is correct:"
echo "   - If Zabbix shows device down 30 min ago"
echo "   - Monitor page should show 'Down 30m' (not 'Down 4h')"
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
