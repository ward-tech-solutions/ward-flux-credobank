#!/bin/bash

echo "================================================================"
echo "  MONITORING ITEMS DIAGNOSTIC"
echo "================================================================"
echo ""

echo "Checking database name..."
DB_NAME=$(docker exec wardops-postgres-prod psql -U ward_admin -l 2>/dev/null | grep ward | awk '{print $1}' | head -1)
echo "Database found: $DB_NAME"
echo ""

echo "Total monitoring items:"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "SELECT COUNT(*) as total_items FROM monitoring_items;" 2>/dev/null

echo ""
echo "Enabled monitoring items:"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "SELECT COUNT(*) as enabled_items FROM monitoring_items WHERE enabled = true;" 2>/dev/null

echo ""
echo "Distinct devices with monitoring items:"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "SELECT COUNT(DISTINCT device_id) as devices_with_items FROM monitoring_items;" 2>/dev/null

echo ""
echo "Monitoring items per device (top 10):"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "
SELECT
    d.name as device_name,
    d.ip,
    COUNT(m.id) as item_count
FROM standalone_devices d
JOIN monitoring_items m ON d.id = m.device_id
WHERE m.enabled = true
GROUP BY d.id, d.name, d.ip
ORDER BY item_count DESC
LIMIT 10;
" 2>/dev/null

echo ""
echo "Monitoring profile mode:"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "SELECT mode, is_active FROM monitoring_profiles ORDER BY created_at DESC LIMIT 1;" 2>/dev/null

echo ""
echo "================================================================"
