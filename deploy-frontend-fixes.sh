#!/bin/bash

set -e  # Exit on any error

echo "================================================================"
echo "  WARD OPS CredoBank - Frontend Fixes Deployment"
echo "================================================================"
echo ""
echo "This script will deploy the following fixes:"
echo "  1. Monitor page: Recently down devices sorting fix"
echo "  2. Devices page: Delete button with confirmation"
echo "  3. Devices page: Toast notifications for all operations"
echo ""
echo "Changes committed:"
git log --oneline -3
echo ""
echo "================================================================"

read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo "Step 1: Pushing changes to remote repository..."
echo "================================================================"
git push origin main

echo ""
echo "Step 2: Rebuilding and restarting containers..."
echo "================================================================"

# Check if we're on production server
if [ -d "/home/wardops/ward-flux-credobank" ]; then
    echo "Detected production server environment"
    cd /home/wardops/ward-flux-credobank

    echo "Pulling latest changes..."
    git pull origin main

    echo "Rebuilding containers..."
    docker-compose -f docker-compose.production-local.yml down
    docker-compose -f docker-compose.production-local.yml up -d --build

    echo "Waiting for containers to start..."
    sleep 10

    echo "Checking container status..."
    docker-compose -f docker-compose.production-local.yml ps

else
    echo "⚠️  Not on production server!"
    echo ""
    echo "Please run the following commands on the production server:"
    echo ""
    echo "  cd /home/wardops/ward-flux-credobank"
    echo "  git pull origin main"
    echo "  docker-compose -f docker-compose.production-local.yml down"
    echo "  docker-compose -f docker-compose.production-local.yml up -d --build"
    echo ""
fi

echo ""
echo "================================================================"
echo "  Deployment Steps Complete!"
echo "================================================================"
echo ""
echo "✅ Changes pushed to repository"
echo "✅ Containers rebuilt (if on production server)"
echo ""
echo "NEXT STEPS - Manual Testing:"
echo ""
echo "1. Monitor Page Testing:"
echo "   - Go to http://your-server/monitor"
echo "   - Unplug a device or block its ping"
echo "   - Wait 30 seconds for detection"
echo "   - Verify device appears at TOP of list"
echo "   - Verify downtime is calculated correctly"
echo ""
echo "2. Devices Page - Delete Testing:"
echo "   - Go to http://your-server/devices"
echo "   - Click red trash icon on a test device"
echo "   - Verify confirmation dialog appears"
echo "   - Click 'Delete' button"
echo "   - Verify success toast appears"
echo "   - Verify device is removed from list"
echo ""
echo "3. Devices Page - Add Device Testing:"
echo "   - Click '+ Add Device' button"
echo "   - Try adding device with duplicate IP"
echo "   - Verify error toast: 'Device with IP X.X.X.X already exists'"
echo "   - Add device with valid data"
echo "   - Verify success toast: 'Device added successfully'"
echo ""
echo "4. Devices Page - Edit Device Testing:"
echo "   - Click edit button on a device"
echo "   - Modify some fields"
echo "   - Click 'Save Changes'"
echo "   - Verify success toast: 'Device updated successfully'"
echo ""
echo "================================================================"
echo ""
echo "If you encounter any issues, check logs with:"
echo "  docker logs wardops-api-prod"
echo "  docker logs wardops-worker-prod"
echo ""
echo "For frontend errors, check browser console (F12)"
echo ""
echo "================================================================"
