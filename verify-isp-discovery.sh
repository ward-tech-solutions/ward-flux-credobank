#!/bin/bash
# Verification script for ISP interface discovery
# Run this on the production server (10.30.25.46)

echo "=========================================="
echo "ISP Interface Discovery Verification"
echo "=========================================="
echo ""

echo "1. Checking discovered interfaces for test router 10.195.57.5..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    d.ip,
    d.name,
    i.if_index,
    i.if_name,
    i.if_alias,
    i.isp_provider,
    CASE
        WHEN i.oper_status = 1 THEN 'UP'
        WHEN i.oper_status = 2 THEN 'DOWN'
        ELSE 'UNKNOWN'
    END as status,
    i.last_polled
FROM standalone_devices d
JOIN device_interfaces i ON d.id = i.device_id
WHERE d.ip = '10.195.57.5'
ORDER BY i.if_index;
"

echo ""
echo "2. Checking total discovered interfaces for all .5 routers..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    COUNT(*) as total_interfaces,
    COUNT(DISTINCT device_id) as devices_with_interfaces
FROM device_interfaces i
JOIN standalone_devices d ON d.id = i.device_id
WHERE d.ip LIKE '%.5';
"

echo ""
echo "3. Checking ISP-specific interfaces (Magti/Silknet)..."
docker exec wardops-postgres-prod psql -U ward_admin -d ward_ops -c "
SELECT
    isp_provider,
    COUNT(*) as interface_count,
    SUM(CASE WHEN oper_status = 1 THEN 1 ELSE 0 END) as up_count,
    SUM(CASE WHEN oper_status = 2 THEN 1 ELSE 0 END) as down_count
FROM device_interfaces i
JOIN standalone_devices d ON d.id = i.device_id
WHERE d.ip LIKE '%.5' AND isp_provider IS NOT NULL
GROUP BY isp_provider;
"

echo ""
echo "4. Checking SNMP worker logs for interface discovery..."
docker logs --tail 50 wardops-worker-snmp-prod | grep -i "interface\|discovery\|10.195.57.5" | tail -20

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
