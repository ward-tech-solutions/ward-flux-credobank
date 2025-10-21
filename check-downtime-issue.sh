#!/bin/bash

echo "================================================================"
echo "  DOWNTIME TRACKING ISSUE DIAGNOSIS"
echo "================================================================"
echo ""

DB_NAME="ward_ops"

echo "Current server time:"
date
echo ""

echo "Device: khashuri-AP (10.195.31.252)"
echo "----------------------------------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "
SELECT
    name,
    ip,
    ping_status,
    down_since,
    NOW() as current_time,
    EXTRACT(EPOCH FROM (NOW() - down_since))/60 as minutes_down,
    updated_at
FROM standalone_devices
WHERE ip = '10.195.31.252' OR name LIKE '%khashuri-AP%'
ORDER BY name;
"

echo ""
echo "All down devices with down_since timestamps:"
echo "----------------------------------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "
SELECT
    name,
    ip,
    down_since,
    EXTRACT(EPOCH FROM (NOW() - down_since))/60 as minutes_down
FROM standalone_devices
WHERE down_since IS NOT NULL
ORDER BY down_since DESC
LIMIT 10;
"

echo ""
echo "Recent worker logs (state transitions):"
echo "----------------------------------------------------------------"
docker logs wardops-worker-prod 2>&1 | grep -E "went DOWN|came back UP|khashuri" | tail -20

echo ""
echo "Recent ping results for khashuri-AP:"
echo "----------------------------------------------------------------"
docker exec wardops-postgres-prod psql -U ward_admin -d "$DB_NAME" -c "
SELECT
    timestamp,
    is_reachable,
    avg_rtt_ms
FROM ping_results
WHERE device_ip = '10.195.31.252'
ORDER BY timestamp DESC
LIMIT 10;
"

echo ""
echo "================================================================"
