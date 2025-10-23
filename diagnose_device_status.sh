#!/bin/bash
# Wrapper script to run device status diagnostic inside Docker container
# Usage: ./diagnose_device_status.sh [device_name_pattern]

DEVICE_PATTERN="${1:-khargauli}"

echo "Running device status diagnostic for: $DEVICE_PATTERN"
echo "=========================================="
echo ""

docker exec wardops-api-prod python3 /app/diagnose_device_status.py "$DEVICE_PATTERN"
