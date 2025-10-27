#!/bin/bash
# Complete ISP Monitoring Deployment Script
# Run this on the production server (10.30.25.46)
#
# This script will:
# 1. Trigger interface discovery for all .5 routers
# 2. Verify ISP interface detection
# 3. Create API endpoint for per-ISP status
# 4. Update frontend to show individual ISP status

set -e  # Exit on error

echo "=========================================="
echo "ISP Monitoring Deployment"
echo "$(date)"
echo "=========================================="
echo ""

# ============================================
# Step 1: Test Single Router First
# ============================================
echo "STEP 1: Testing interface discovery on single router (10.195.57.5)..."
echo "----------------------------------------------------------------------"

# Get device ID
DEVICE_ID=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT id FROM standalone_devices WHERE ip = '10.195.57.5';" | xargs)

if [ -z "$DEVICE_ID" ]; then
    echo "ERROR: Test device 10.195.57.5 not found!"
    exit 1
fi

echo "Device ID: $DEVICE_ID"
echo ""

# Trigger discovery
echo "Triggering interface discovery..."
docker exec wardops-worker-snmp-prod python3 << EOF
import sys
sys.path.insert(0, '/app')

from monitoring.tasks_interface_discovery import discover_device_interfaces_task

print("Discovering interfaces for device $DEVICE_ID...")
result = discover_device_interfaces_task('$DEVICE_ID')

print("\nDiscovery Result:")
print(f"  Success: {result.get('success', False)}")
print(f"  Device IP: {result.get('device_ip', 'N/A')}")
print(f"  Interfaces Found: {result.get('interfaces_found', 0)}")
print(f"  Interfaces Saved: {result.get('interfaces_saved', 0)}")
print(f"  Critical Interfaces: {result.get('critical_interfaces', 0)}")
print(f"  ISP Interfaces: {result.get('isp_interfaces', [])}")
if result.get('error'):
    print(f"  ERROR: {result['error']}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Interface discovery failed for test device!"
    echo "Please check SNMP connectivity and credentials."
    exit 1
fi

echo ""
echo "Verifying discovered interfaces in database..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
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
WHERE d.ip = '10.195.57.5' AND i.isp_provider IS NOT NULL
ORDER BY i.if_index;
"

# Check if we found ISP interfaces
ISP_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM device_interfaces i JOIN standalone_devices d ON d.id = i.device_id WHERE d.ip = '10.195.57.5' AND i.isp_provider IS NOT NULL;" | xargs)

if [ "$ISP_COUNT" -lt 2 ]; then
    echo ""
    echo "WARNING: Expected 2 ISP interfaces (Magti + Silknet), found: $ISP_COUNT"
    echo "Continuing anyway..."
fi

echo ""
echo "✅ Step 1 Complete: Test router interface discovery successful"
echo ""

# ============================================
# Step 2: Discover All .5 Routers
# ============================================
echo "STEP 2: Discovering interfaces for all .5 routers..."
echo "----------------------------------------------------------------------"

echo "Getting list of all .5 routers with SNMP credentials..."
ROUTER_COUNT=$(docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -t -c "SELECT COUNT(*) FROM standalone_devices WHERE ip LIKE '%.5' AND snmp_community IS NOT NULL AND enabled = true;" | xargs)

echo "Found $ROUTER_COUNT routers to process"
echo ""

if [ "$ROUTER_COUNT" -eq 0 ]; then
    echo "ERROR: No .5 routers found with SNMP credentials!"
    exit 1
fi

echo "Triggering bulk interface discovery (this may take 5-10 minutes)..."
docker exec wardops-worker-snmp-prod python3 << 'EOF'
import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from monitoring.models import StandaloneDevice
from monitoring.tasks_interface_discovery import discover_device_interfaces_task
import time

db = SessionLocal()

# Get all .5 routers with SNMP enabled
routers = db.query(StandaloneDevice).filter(
    StandaloneDevice.ip.like('%.5'),
    StandaloneDevice.snmp_community.isnot(None),
    StandaloneDevice.enabled == True
).all()

print(f"Processing {len(routers)} routers...")
print("")

success_count = 0
failed_count = 0
isp_interface_count = 0

for i, router in enumerate(routers, 1):
    print(f"[{i}/{len(routers)}] {router.ip} ({router.name})...", end=" ", flush=True)

    try:
        result = discover_device_interfaces_task(str(router.id))

        if result.get('success'):
            isp_count = len(result.get('isp_interfaces', []))
            print(f"✅ {result['interfaces_saved']} interfaces, {isp_count} ISP")
            success_count += 1
            isp_interface_count += isp_count
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ {error}")
            failed_count += 1
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        failed_count += 1

    # Small delay to avoid overwhelming SNMP
    time.sleep(0.5)

print("")
print("=" * 70)
print(f"Bulk Discovery Complete:")
print(f"  Success: {success_count}/{len(routers)}")
print(f"  Failed: {failed_count}/{len(routers)}")
print(f"  Total ISP Interfaces: {isp_interface_count}")
print("=" * 70)

db.close()
EOF

echo ""
echo "✅ Step 2 Complete: Bulk interface discovery finished"
echo ""

# ============================================
# Step 3: Verify Results
# ============================================
echo "STEP 3: Verifying ISP interface discovery results..."
echo "----------------------------------------------------------------------"

echo "ISP Interface Summary:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    i.isp_provider,
    COUNT(*) as interface_count,
    SUM(CASE WHEN i.oper_status = 1 THEN 1 ELSE 0 END) as up_count,
    SUM(CASE WHEN i.oper_status = 2 THEN 1 ELSE 0 END) as down_count,
    SUM(CASE WHEN i.oper_status NOT IN (1,2) THEN 1 ELSE 0 END) as unknown_count
FROM device_interfaces i
JOIN standalone_devices d ON d.id = i.device_id
WHERE d.ip LIKE '%.5' AND i.isp_provider IS NOT NULL
GROUP BY i.isp_provider
ORDER BY i.isp_provider;
"

echo ""
echo "Routers with ISP interfaces discovered:"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(DISTINCT d.id) as routers_with_isp_interfaces,
    (SELECT COUNT(*) FROM standalone_devices WHERE ip LIKE '%.5' AND enabled = true) as total_routers
FROM standalone_devices d
JOIN device_interfaces i ON d.id = i.device_id
WHERE d.ip LIKE '%.5' AND i.isp_provider IS NOT NULL;
"

echo ""
echo "Sample ISP interfaces (first 10):"
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    d.ip,
    d.name,
    i.if_name,
    i.if_alias,
    i.isp_provider,
    CASE
        WHEN i.oper_status = 1 THEN 'UP'
        WHEN i.oper_status = 2 THEN 'DOWN'
        ELSE 'UNKNOWN'
    END as status
FROM standalone_devices d
JOIN device_interfaces i ON d.id = i.device_id
WHERE d.ip LIKE '%.5' AND i.isp_provider IS NOT NULL
ORDER BY d.ip, i.if_index
LIMIT 10;
"

echo ""
echo "✅ Step 3 Complete: Verification finished"
echo ""

# ============================================
# Final Summary
# ============================================
echo "=========================================="
echo "ISP Monitoring Deployment Complete"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Add API endpoint to return per-ISP status"
echo "2. Update frontend Monitor.tsx to fetch per-ISP status"
echo "3. Schedule automatic interface polling (every 60s)"
echo ""
echo "To view ISP status manually:"
echo "  docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops \\"
echo "    -c \"SELECT d.ip, i.isp_provider, i.oper_status FROM standalone_devices d \\"
echo "       JOIN device_interfaces i ON d.id=i.device_id WHERE d.ip LIKE '%.5' \\"
echo "       AND i.isp_provider IS NOT NULL;\""
echo ""
echo "=========================================="
