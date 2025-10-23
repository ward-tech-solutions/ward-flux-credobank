#!/bin/bash
# Check what code is actually deployed in the container

echo "Checking deployed code in wardops-api-prod container..."
echo "=========================================="
echo ""
echo "Looking for 'Failed to save ping record' line in routers/devices.py:"
docker exec wardops-api-prod grep -n "Failed to save ping record" /app/routers/devices.py

echo ""
echo "Checking entire _store_ping_result function:"
docker exec wardops-api-prod sed -n '373,411p' /app/routers/devices.py
