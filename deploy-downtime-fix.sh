#!/bin/bash

set -e

echo "=================================================================="
echo "  WARD OPS - Downtime Calculation Fix Deployment"
echo "=================================================================="
echo ""
echo "This will deploy the following fixes:"
echo "  1. Proper state transition detection (UP->DOWN, DOWN->UP)"
echo "  2. Timezone-aware timestamp handling"
echo "  3. Self-healing for stale/missing down_since timestamps"
echo "  4. Delete button functionality"
echo "  5. Toast notifications for all operations"
echo ""
echo "=================================================================="
echo ""

# Check if running on production server
if [ -d "/home/wardops/ward-flux-credobank" ]; then
    echo "✓ Detected production server environment"
    cd /home/wardops/ward-flux-credobank
else
    echo "Please run this on the production server or specify the correct path"
    exit 1
fi

echo ""
echo "Step 1: Pulling latest code from repository..."
echo "=================================================================="
git fetch origin
git log --oneline HEAD..origin/main | head -10

echo ""
read -p "Do you want to proceed with these changes? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

git pull origin main

echo ""
echo "Step 2: Restarting worker container (ping tasks)..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml restart wardops-worker-prod

echo ""
echo "Waiting for worker to start..."
sleep 5

echo ""
echo "Step 3: Verifying worker status..."
echo "=================================================================="
docker logs wardops-worker-prod --tail 30

echo ""
echo "Step 4: Rebuilding frontend (delete button + toast notifications)..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml up -d --build

echo ""
echo "Waiting for containers to start..."
sleep 10

echo ""
echo "Step 5: Verifying all containers are running..."
echo "=================================================================="
docker-compose -f docker-compose.production-local.yml ps

echo ""
echo "=================================================================="
echo "  Deployment Complete!"
echo "=================================================================="
echo ""
echo "✅ Backend fixes deployed (state transition detection)"
echo "✅ Frontend fixes deployed (delete button + toasts)"
echo "✅ Worker restarted with new code"
echo ""
echo "NEXT STEPS - Testing:"
echo ""
echo "1. Monitor worker logs for state transitions:"
echo "   docker logs wardops-worker-prod -f | grep -E 'went DOWN|came back UP|stale|missing'"
echo ""
echo "2. Open Monitor page in browser and check:"
echo "   - Downtime shows correct values (not 4h for new outages)"
echo "   - Recently down devices appear at top"
echo "   - Press F12 to see debug logs with actual timestamps"
echo ""
echo "3. Test delete button on Devices page:"
echo "   - Click red trash icon on a device"
echo "   - Verify confirmation dialog appears"
echo "   - Verify success/error toasts appear"
echo ""
echo "4. Test duplicate IP detection:"
echo "   - Try adding device with existing IP"
echo "   - Should see error toast with specific message"
echo ""
echo "=================================================================="
echo ""
echo "Monitoring Commands:"
echo ""
echo "# Watch for state transitions:"
echo "docker logs wardops-worker-prod -f | grep -E 'went DOWN|came back UP'"
echo ""
echo "# Check for stale data being cleaned:"
echo "docker logs wardops-worker-prod | grep -E 'stale|missing'"
echo ""
echo "# View API logs:"
echo "docker logs wardops-api-prod -f"
echo ""
echo "=================================================================="
