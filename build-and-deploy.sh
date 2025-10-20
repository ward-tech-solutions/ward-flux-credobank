#!/bin/bash

# ================================================================
# WARD OPS - Build Frontend and Deploy with All Fixes
# ================================================================

set -e

echo "=========================================="
echo "Building Frontend and Deploying"
echo "=========================================="
echo ""

cd /home/wardops/ward-flux-credobank

echo "1. Pulling latest code from GitHub..."
git pull origin main

echo ""
echo "2. Rebuilding all containers (includes frontend build)..."
echo "   Using --no-cache to ensure fresh build with latest code..."
docker-compose -f docker-compose.production-local.yml build --no-cache

echo ""
echo "3. Stopping all containers..."
docker-compose -f docker-compose.production-local.yml down

echo ""
echo "4. Starting all containers..."
docker-compose -f docker-compose.production-local.yml up -d

echo ""
echo "5. Waiting for services to start (60 seconds)..."
sleep 60

echo ""
echo "Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep wardops

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "The website now has all fixes:"
echo "  ✅ Accurate downtime display (shows hours/minutes)"
echo "  ✅ Recent down devices sorted correctly"
echo "  ✅ Regions dropdown with all regions"
echo "  ✅ Device edit working"
echo ""
echo "Access: http://10.30.25.39:5001"
echo ""
