#!/bin/bash
# Trigger ISP interface discovery for .5 routers
# Run this on the production server (10.30.25.46)

echo "=========================================="
echo "ISP Interface Discovery - Manual Trigger"
echo "=========================================="
echo ""

# Get device ID for test router 10.195.57.5
echo "1. Getting device ID for 10.195.57.5..."
DEVICE_ID=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT id FROM standalone_devices WHERE ip = '10.195.57.5';")
DEVICE_ID=$(echo $DEVICE_ID | xargs)  # Trim whitespace

if [ -z "$DEVICE_ID" ]; then
    echo "ERROR: Device 10.195.57.5 not found in database!"
    exit 1
fi

echo "   Device ID: $DEVICE_ID"
echo ""

# Trigger interface discovery task
echo "2. Triggering interface discovery task..."
docker exec wardops-worker-snmp-prod python3 << EOF
import sys
sys.path.insert(0, '/app')

from monitoring.tasks_interface_discovery import discover_device_interfaces_task

print("Calling discover_device_interfaces_task for device $DEVICE_ID...")
result = discover_device_interfaces_task('$DEVICE_ID')

print("")
print("Discovery Result:")
print(f"  Success: {result.get('success', False)}")
print(f"  Device IP: {result.get('device_ip', 'N/A')}")
print(f"  Interfaces Found: {result.get('interfaces_found', 0)}")
print(f"  Interfaces Saved: {result.get('interfaces_saved', 0)}")
print(f"  Critical Interfaces: {result.get('critical_interfaces', 0)}")
print(f"  ISP Interfaces: {result.get('isp_interfaces', [])}")
if result.get('error'):
    print(f"  Error: {result['error']}")
print(f"  Skipped Loopback: {result.get('skipped_loopback', 0)}")
EOF

echo ""
echo "3. Checking discovered interfaces in database..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    d.ip,
    d.name,
    i.if_index,
    i.if_name,
    i.if_alias,
    i.isp_provider,
    i.interface_type,
    i.is_critical,
    CASE
        WHEN i.oper_status = 1 THEN 'UP'
        WHEN i.oper_status = 2 THEN 'DOWN'
        ELSE 'UNKNOWN'
    END as status
FROM standalone_devices d
JOIN device_interfaces i ON d.id = i.device_id
WHERE d.ip = '10.195.57.5'
ORDER BY i.if_index;
"

echo ""
echo "=========================================="
echo "Discovery Complete"
echo "=========================================="
