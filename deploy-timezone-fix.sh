#!/bin/bash

set -e

echo "=================================================================="
echo "  WARD OPS - Timezone Fix Deployment"
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
echo "Step 2: Stopping containers..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml stop api celery-worker

echo ""
echo "Step 3: Rebuilding images (this will take 2-3 minutes)..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml build --no-cache api celery-worker

echo ""
echo "Step 4: Starting containers..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml up -d api celery-worker

echo ""
echo "Waiting for containers to start..."
sleep 10

echo ""
echo "Step 5: Verifying containers are running..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml ps api celery-worker

echo ""
echo "Step 6: Testing API response..."
echo "=================================================================="
echo "Waiting 5 more seconds for API to be ready..."
sleep 5

echo ""
echo "Checking if down_since timestamps now include timezone..."
echo ""

# Make API call to get devices and check timestamp format
curl -s http://localhost:5001/api/v1/devices/standalone | jq -r '.[] | select(.down_since != null) | "\(.name): \(.down_since)"' | head -3

echo ""
echo "=================================================================="
echo "  Deployment Complete!"
echo "=================================================================="
echo ""
echo "✅ API container rebuilt with new code"
echo "✅ Worker container rebuilt with new code"
echo ""
echo "VERIFICATION STEPS:"
echo ""
echo "1. Check that down_since timestamps now have timezone (+00:00 suffix):"
echo "   curl http://localhost:5001/api/v1/devices/standalone | jq '.[] | select(.down_since != null) | .down_since'"
echo ""
echo "2. Open Monitor page in browser and check console (F12):"
echo "   - down_since should show: 2025-10-21T08:34:45.186571+00:00"
echo "   - Diff hours should be small (< 1.0 for recent outages)"
echo ""
echo "3. Watch worker logs for state transitions:"
echo "   docker logs wardops-worker-prod -f | grep -E 'went DOWN|came back UP'"
echo ""
echo "=================================================================="
