#!/bin/bash
# Wrapper script to run device status diagnostic inside Docker container
# Usage: ./diagnose_device_status.sh [device_name_pattern]

DEVICE_PATTERN="${1:-khargauli}"

echo "Running device status diagnostic for: $DEVICE_PATTERN"
echo "=========================================="
echo ""

# Copy script into container and run it
docker cp diagnose_device_status.py wardops-api-prod:/tmp/diagnose_device_status.py
docker exec wardops-api-prod python3 /tmp/diagnose_device_status.py "$DEVICE_PATTERN"
