#!/bin/bash

echo "================================================================"
echo "  DUPLICATE IP ADDRESS DIAGNOSTIC"
echo "================================================================"
echo ""

echo "Finding database name..."
DB_NAME=$(docker exec wardops-postgres-prod psql -U ward_admin -l 2>/dev/null | grep ward | awk '{print $1}' | head -1)
echo "Database: $DB_NAME"
echo ""

echo "Duplicate IP addresses:"
echo "----------------------------------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "
SELECT
    ip,
    COUNT(*) as device_count,
    STRING_AGG(name, ', ') as device_names
FROM standalone_devices
GROUP BY ip
HAVING COUNT(*) > 1
ORDER BY device_count DESC, ip;
" 2>/dev/null

echo ""
echo "Full details of devices with duplicate IPs:"
echo "----------------------------------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "
SELECT
    d.ip,
    d.id,
    d.name,
    d.normalized_name,
    d.device_type,
    d.enabled,
    b.display_name as branch_name,
    d.created_at
FROM standalone_devices d
LEFT JOIN branches b ON d.branch_id = b.id
WHERE d.ip IN (
    SELECT ip
    FROM standalone_devices
    GROUP BY ip
    HAVING COUNT(*) > 1
)
ORDER BY d.ip, d.created_at;
" 2>/dev/null

echo ""
echo "================================================================"
